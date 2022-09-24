import pysolr
from django.core.management import BaseCommand

from frontend import settings
from frontend.risdb.models import Document


class Command(BaseCommand):
    help = "Update solr from risdb"

    DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    DEFAULT_CHUNK_SIZE = 100

    def add_arguments(self, parser):
        parser.add_argument("--chunk_size",
                            help=f"chunk size for document processing (default: {self.DEFAULT_CHUNK_SIZE})",
                            type=int)

    def _connect_solr(self):
        solr = pysolr.Solr(f"{settings.SOLR_HOST}/{settings.SOLR_COLLECTION}")
        result = solr.ping()
        assert("OK" in result)
        return solr

    def _to_solr(self, doc):
        solr_doc = dict(
            doc_type="document",
            id=str(doc.id),
            document_id=doc.document_id,
            size=doc.size,
            content=doc.content_text,
            content_ocr=doc.content_text_ocr,
            author=doc.author,
            content_type=doc.content_type
        )

        consultations = doc.consultations.all()
        consultation = None
        if len(consultations) > 1:
            raise ValueError("Associated consultation objects > 1. This is unexpected")
        elif len(consultations) == 1:
            consultation = consultations[0]
        if consultation is not None:
            solr_doc["consultation_id"] = consultation.consultation_id
            solr_doc["consultation_name"] = consultation.name
            solr_doc["consultation_topic"] = consultation.topic
            solr_doc["consultation_type"] = consultation.type
            solr_doc["consultation_text"] = consultation.text

        if doc.creation_date is not None:
            solr_doc['creation_date'] = doc.creation_date.strftime(self.DATE_FORMAT),
        if doc.last_modified is not None:
            solr_doc['last_modified'] = doc.last_modified.strftime(self.DATE_FORMAT),
        if doc.last_saved is not None:
            solr_doc['last_saved'] = doc.last_saved.strftime(self.DATE_FORMAT),
        return solr_doc

    def handle(self, *args, **options):
        processed = 0
        chunk_size = self.DEFAULT_CHUNK_SIZE
        if options['chunk_size']:
            chunk_size = options['chunk_size']
        solr = self._connect_solr()
        solr_docs = []
        for document in Document.objects.all().iterator(chunk_size):
            solr_doc = self._to_solr(document)
            solr_docs.append(solr_doc)
            if len(solr_docs) >= chunk_size:
                solr.add(solr_docs, commit=False)
                self.stdout.write(f"Submitted {chunk_size} documents to solr.")
                processed += len(solr_docs)
                solr_docs = []
        solr.add(solr_docs, commit=True)
        processed += len(solr_docs)
        self.stdout.write(f"{processed} documents processed.")


