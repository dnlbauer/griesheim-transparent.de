import json
import os
import re
from typing import Any

import pysolr
from django.conf import settings
from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from frontend.processing.external_services import (
    ExternalServiceUnsuccessfulException,
    analyze_document_pdfact,
    analyze_document_tika,
    convert_to_pdf,
    get_preview_image_for_doc,
)
from frontend.processing.file_repository import FileRepository
from frontend.processing.processing import SolrImportDoc, parse_solr_document
from ris.models import Document


class Command(BaseCommand):
    help = "Update solr index from ris database"

    DEFAULT_CHUNK_SIZE = 10  # chunk size for solr document commit

    def __init__(self) -> None:
        super().__init__()
        self.file_repository = FileRepository()
        self.solr = pysolr.Solr(f"{settings.SOLR_HOST}/{settings.SOLR_COLLECTION}")
        self.processed = 0
        self.total = Document.objects.all().count()

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--chunk_size",
            help=f"chunk size for sending documents to solr (default: {self.DEFAULT_CHUNK_SIZE})",
            type=int,
            default=self.DEFAULT_CHUNK_SIZE,
        )
        parser.add_argument(
            "--force", help="force update for all documents", action="store_true"
        )
        parser.add_argument(
            "--no-ocr",
            help="allow ocr for documents (takes a long time)",
            action="store_false",
        )
        parser.add_argument(
            "-o", help="Output file: Also store results in this file as json lines"
        )

    def _parse_args(self, **options: Any) -> None:
        self.chunk_size = self.DEFAULT_CHUNK_SIZE
        self.force = options["force"]
        self.allow_ocr = options["no_ocr"]
        if options["o"]:
            try:
                os.unlink(options["o"])
            except FileNotFoundError:
                pass
            self.output = options["o"]
        else:
            self.output = None

    def handle(self, *args: Any, **options: Any) -> None:
        self._parse_args(**options)
        print(f"Processing {self.total} documents...")

        solr_docs = []

        for document in Document.objects.all():
            print(f"Processing {document.file_name} (id={str(document.id)})")

            repository_file_path: str = self.file_repository.get_file_path(document.uri)
            if document.content_type and not document.content_type.lower().endswith(
                "pdf"
            ):
                try:
                    file_path = convert_to_pdf(
                        repository_file_path, skip_cache=self.force
                    )
                except ExternalServiceUnsuccessfulException:
                    file_path = None
            else:
                file_path = repository_file_path

            # perform text analysis
            content: list[str] | None = []
            metadata: dict[str, Any] = {}
            preview_image = None
            if file_path is not None:
                print("Sending document to pdfact")
                try:
                    content = analyze_document_pdfact(file_path, skip_cache=self.force)
                except ExternalServiceUnsuccessfulException:
                    content = None

                # analyze document with tika
                print("Sending document to tika")
                tika_result = analyze_document_tika(
                    file_path, False, skip_cache=self.force
                )

                # use tika content if pdfact returned nothing
                if not content:
                    if tika_result and tika_result["content"] is not None:
                        content = [tika_result["content"].strip()]
                        if content and len(content) == 0:
                            content = None

                    # Run OCR/tesseract if there is no content from tika without ocr
                    if self.allow_ocr and (not content or content == "Page 1"):
                        print("PDF has no text content. Sending document to tika/ocr")
                        tika_result = analyze_document_tika(
                            file_path, True, skip_cache=self.force
                        )
                        if tika_result and tika_result["content"] is not None:
                            content = [tika_result["content"].strip()]
                            if content and len(content) == 0:
                                content = None

                metadata = tika_result["metadata"] if tika_result else {}

                if content:
                    content = [
                        re.sub(r"(\n)\n+", "\n", paragraph) for paragraph in content
                    ]  # replace multiple new lines

                print("Sending document to preview service")
                try:
                    preview_image = get_preview_image_for_doc(
                        file_path, skip_cache=self.force
                    )
                except ExternalServiceUnsuccessfulException as e:
                    # Empty preview image
                    print(f"Failed to get preview image for {file_path}: {e}")
                    preview_image = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

            solr_doc = parse_solr_document(document, content, metadata, preview_image)
            solr_docs.append(solr_doc)

            # write document to solr in chunks
            if len(solr_docs) >= self.chunk_size:
                self.submit(solr_docs)
                solr_docs = []

        self.submit(solr_docs, commit=True)
        print(f"Processed {self.processed} documents.")

    def submit(self, solr_docs: list[SolrImportDoc], commit: bool = False) -> None:
        self.processed += len(solr_docs)
        print(
            f"Submitting {len(solr_docs)} documents to solr. (Processed={self.processed}/{self.total})"
        )
        self.solr.add(solr_docs, commit=commit)
        if self.output:
            with open(self.output, "a", encoding="utf-8") as f:
                for solr_doc in solr_docs:
                    f.write(f"{json.dumps(solr_doc, ensure_ascii=False)}\n")
