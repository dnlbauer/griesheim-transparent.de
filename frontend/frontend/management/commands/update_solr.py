from datetime import datetime

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
        return solr

    def _to_solr(self, doc):
        solr_doc = dict(
            id=str(doc.id),
            document_id=doc.document_id,
            size=doc.size,
            content=doc.content_text,
            content_ocr=doc.content_text_ocr,
            author=doc.author,
            content_type=doc.content_type,
            meeting_id=[],
            meeting_title=[],
            meeting_title_short=[],
            meeting_date=[],
            meeting_organization_name=[],
            filename=doc.file_name
        )
        meetings = []
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
            solr_doc['doc_type'] = consultation.type

            agenda_items = consultation.agenda_items.all()
            for item in agenda_items:
                meetings.append(item.meeting)
        if 'doc_type' not in solr_doc:
            if (doc.content_text and "niederschrift" in doc.content_text[:100].lower()) or (doc.content_text_ocr and "niederschrift" in doc.content_text_ocr[:100].lower()):
                solr_doc['doc_type'] = "Niederschrift"

        meetings += doc.meetings.all()
        for meeting in meetings:
            if meeting.meeting_id not in solr_doc['meeting_id']:
                solr_doc['meeting_id'].append(meeting.meeting_id)
                solr_doc['meeting_title'].append(meeting.title)
                solr_doc['meeting_title_short'].append(meeting.title_short)
                solr_doc['meeting_date'].append(meeting.date.strftime(self.DATE_FORMAT))
                solr_doc['meeting_organization_name'].append(meeting.organization.name)
                if "last_seen" not in solr_doc or datetime.strptime(solr_doc['last_seen'], self.DATE_FORMAT) < meeting.date:
                    solr_doc['last_seen'] = solr_doc['meeting_date'][-1]
                if "first_seen" not in solr_doc or datetime.strptime(solr_doc['first_seen'], self.DATE_FORMAT) > meeting.date:
                    solr_doc['first_seen'] = solr_doc['meeting_date'][-1]

        solr_doc['meeting_count'] = len(solr_doc['meeting_id'])

        if 'doc_type' in solr_doc and solr_doc['doc_type'] == 'Niederschrift':
            solr_doc['doc_title'] = meeting.title
        elif "consultation_name" in solr_doc:
            solr_doc['doc_title'] = solr_doc['consultation_topic']

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
                solr.add(solr_docs, commit=True)
                self.stdout.write(f"Submitted {chunk_size} documents to solr.")
                processed += len(solr_docs)
                solr_docs = []
        solr.add(solr_docs, commit=True)
        processed += len(solr_docs)
        self.stdout.write(f"{processed} documents processed.")


