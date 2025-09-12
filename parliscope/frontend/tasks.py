import re
from typing import Any

import pysolr
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings

from frontend.processing.external_services import (
    ExternalServiceUnsuccessfulException,
    analyze_document_pdfact,
    analyze_document_tika,
    convert_to_pdf,
    get_preview_image_for_doc,
)
from frontend.processing.file_repository import FileRepository
from frontend.processing.processing import SolrImportDoc, parse_solr_document
from models.models import Document

logger = get_task_logger(__name__)


@shared_task(bind=True)
def update_solr_index(self, force=False, allow_ocr=True, chunk_size=10):
    """
    Celery task to update Solr index from RIS database.

    Args:
        force (bool): Force update for all documents
        allow_ocr (bool): Allow OCR for documents (takes a long time)
        chunk_size (int): Chunk size for sending documents to Solr
    """
    logger.info("Starting Solr index update task")

    file_repository = FileRepository()
    solr = pysolr.Solr(f"{settings.SOLR_HOST}/{settings.SOLR_COLLECTION}")

    solr_docs = []  # Batch of documents to send to Solr
    total = Document.objects.all().count()
    processed = 0

    def submit(solr_docs: list[SolrImportDoc], commit: bool = False) -> None:
        logger.info(
            f"Submitting {len(solr_docs)} documents to solr. (Processed={processed}/{total})"
        )
        solr.add(solr_docs, commit=commit)

    for document in Document.objects.all():
        document_name = document.file_name
        print(f"Processing {document_name} (id={str(document.id)})")

        repository_file_path: str = file_repository.get_file_path(document.uri)
        if document.content_type and not document.content_type.lower().endswith("pdf"):
            try:
                file_path = convert_to_pdf(repository_file_path, skip_cache=force)
            except ExternalServiceUnsuccessfulException:
                file_path = None
        else:
            file_path = repository_file_path

        # perform text analysis
        content: list[str] | None = []
        metadata: dict[str, Any] = {}
        preview_image = None
        if file_path is not None:
            logger.info(f"Sending document {document_name} to pdfact")
            try:
                content = analyze_document_pdfact(file_path, skip_cache=force)
            except ExternalServiceUnsuccessfulException:
                content = None

            # analyze document with tika
            logger.info(f"Sending document {document_name} to tika")
            tika_result = analyze_document_tika(file_path, False, skip_cache=force)

            # use tika content if pdfact returned nothing
            if not content:
                if tika_result and tika_result["content"] is not None:
                    content = [tika_result["content"].strip()]
                    if content and len(content) == 0:
                        content = None

                # Run OCR/tesseract if there is no content from tika without ocr
                if allow_ocr and (not content or content == "Page 1"):
                    logger.info(
                        f"PDF {document_name} has no text content. Sending document to tika/ocr"
                    )
                    tika_result = analyze_document_tika(
                        file_path, True, skip_cache=force
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

            logger.info(f"Sending document {document_name} to preview service")
            try:
                preview_image = get_preview_image_for_doc(file_path, skip_cache=force)
            except ExternalServiceUnsuccessfulException as e:
                # Empty preview image
                logger.warning(f"Failed to get preview image for {file_path}: {e}")
                preview_image = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="

        solr_doc = parse_solr_document(document, content, metadata, preview_image)
        solr_docs.append(solr_doc)

        # write document to solr in chunks
        if len(solr_docs) >= chunk_size:
            submit(solr_docs)
            processed += len(solr_docs)
            self.update_state(
                state="PROGRESS",
                meta={"processed": processed + len(solr_docs), "total": total},
            )
            solr_docs.clear()

    submit(solr_docs, commit=True)
    processed += len(solr_docs)
    logger.info(f"Processed {processed} documents. all done.")
