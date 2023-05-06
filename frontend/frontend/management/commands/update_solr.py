import re

import pysolr
from django.core.management import BaseCommand

from frontend import settings
from frontend.processing.file_repository import FileRepository
from frontend.processing.external_services import get_preview_image_for_doc, analyze_document_pdfact, analyze_document_tika, \
    convert_to_pdf
from frontend.processing.processing import parse_solr_document
from ris.models import Document


class Command(BaseCommand):
    help = "Update solr index from risdb"

    DEFAULT_CHUNK_SIZE = 10  # chunk size for solr document commit

    def __init__(self):
        super().__init__()
        self.file_repository = FileRepository()

    def add_arguments(self, parser):
        parser.add_argument("--chunk_size",
                            help=f"chunk size for sending documents to solr (default: {self.DEFAULT_CHUNK_SIZE})",
                            type=int,
                            default=self.DEFAULT_CHUNK_SIZE
                            )
        parser.add_argument("--force",
                            help="force update for all documents",
                            action="store_true")
        parser.add_argument("--no-ocr",
                            help="allow ocr for documents (takes a long time)",
                            action="store_false")

    def _log(self, message):
        self.stdout.write(message)

    def _parse_args(self, **options):
        self.chunk_size = self.DEFAULT_CHUNK_SIZE
        self.force = options["force"]
        self.allow_ocr = options["no_ocr"]


    def handle(self, *args, **options):
        self._parse_args(**options)

        solr = pysolr.Solr(f"{settings.SOLR_HOST}/{settings.SOLR_COLLECTION}")
        solr_docs = []

        total = Document.objects.all().count()
        self._log(f"Processing {total} documents...")

        processed = 0
        for document in Document.objects.all():
            self._log(f"Processing {document.file_name} ({str(document.id)})")

            # perform text analysis
            content = []
            metadata = {}
            preview_image = None
            file_path = self.file_repository.get_file_path(document.uri)
            if not document.content_type.lower().endswith("pdf"):
                file_path = convert_to_pdf(file_path, skip_cache=self.force)

            if file_path is not None:
                self._log("Sending document to pdfact")
                content = analyze_document_pdfact(file_path, skip_cache=self.force)

                # analyze document with tika
                self._log("Sending document to tika")
                tika_result = analyze_document_tika(file_path, False, skip_cache=self.force)

                # Run OCR/tesseract if there is no content from tika without ocr
                tika_content = tika_result["content"].strip() if (
                            tika_result is not None and tika_result["content"] is not None) else None
                if self.allow_ocr and content is None and (
                        tika_content is None or len(tika_content) == 0 or tika_content == "Page 1"):
                    self._log("Sending document to tika/ocr")
                    tika_result = analyze_document_tika(file_path, True, skip_cache=self.force)
                    tika_content = tika_result["content"].strip() if (tika_result and tika_result["content"]) else None

                metadata = tika_result["metadata"]
                if (content is None or len(content) == 0) and tika_content is not None:
                    content = re.sub(r"(\n)\n+", "\n", tika_content)  # replace multiple new lines

                self._log("Sending document to preview service")
                preview_image = get_preview_image_for_doc(file_path, skip_cache=self.force)

            # generate solr document from data
            solr_doc = parse_solr_document(document, content, metadata, preview_image)
            solr_docs.append(solr_doc)
            processed += 1

            # write chunks to solr
            if len(solr_docs) >= self.chunk_size:
                self._log(f"Submitting {len(solr_docs)} documents to solr. (Processed={processed}/{total})")
                solr.add(solr_docs)
                solr_docs = []

        # commit last incomplete chunk
        solr.add(solr_docs, commit=True)
        self._log(f"Submitting {len(solr_docs)} documents to solr. (Processed={processed}/{total})")
        self._log(f"Processed {processed} documents.")

