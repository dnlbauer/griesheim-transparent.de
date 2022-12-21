from datetime import datetime

import pysolr
from django.core.management import BaseCommand

from frontend import settings
from frontend.risdb.models import Document
from frontend.utils import get_preview_image_for_doc


class Command(BaseCommand):
    help = "Update solr from risdb"

    DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    DEFAULT_CHUNK_SIZE = 10
    VERSION = 2  # incr. if analyze chain changes

    def add_arguments(self, parser):
        parser.add_argument("--chunk_size",
                            help=f"chunk size for document processing (default: {self.DEFAULT_CHUNK_SIZE})",
                            type=int)

    def _connect_solr(self):
        solr = pysolr.Solr(f"{settings.SOLR_HOST}/{settings.SOLR_COLLECTION}")
        return solr

    def _to_solr(self, doc):
        # find corresponding consultation
        consultations = doc.consultations.all()
        consultation = None
        if len(consultations) > 1:
            raise ValueError("Associated consultation objects > 1. This is unexpected")
        elif len(consultations) == 1:
            consultation = consultations[0]

        # find associated meetings and agenda items
        meetings = set(doc.meetings.all())
        agenda_items = set(doc.agenda_items.all())

        if consultation is not None:
            consultation_agenda_items = consultation.agenda_items.all()
            for item in consultation_agenda_items:
                agenda_items.add(item)
                meetings.add(item.meeting)
            consultation_meetings = consultation.meetings.all()
            for item in consultation_meetings:
                meetings.add(item)

        # create document
        solr_doc = dict(
            version=self.VERSION,
            last_analyzed=datetime.now().strftime(self.DATE_FORMAT),
            id=str(doc.id),
            document_id=doc.document_id,
            size=doc.size,
            content=doc.content_text,
            content_ocr=doc.content_text_ocr,
            author=doc.author,
            content_type=doc.content_type,
            doc_title=doc.title,
            agenda_item_id=[],
            agenda_item_title=[],
            agenda_item_text=[],
            meeting_id=[],
            meeting_title=[],
            meeting_title_short=[],
            meeting_date=[],
            meeting_organization_name=[],
            filename=doc.file_name,
            preview_image=get_preview_image_for_doc(doc.document_id)
        )

        if consultation is not None:
            solr_doc["consultation_id"] = consultation.consultation_id
            solr_doc["consultation_name"] = consultation.name
            solr_doc["consultation_topic"] = consultation.topic
            solr_doc["consultation_type"] = consultation.type
            solr_doc["consultation_text"] = consultation.text
            solr_doc['doc_type'] = consultation.type

        # Niederschrift recognized by content
        if 'doc_type' not in solr_doc or solr_doc['doc_type'] is None:
            if (doc.content_text and "niederschrift" in doc.content_text[:100].lower()) or (doc.content_text_ocr and "niederschrift" in doc.content_text_ocr[:100].lower()):
                solr_doc['doc_type'] = "Niederschrift"

        for agenda_item in agenda_items:
            if agenda_item.agenda_item_id not in solr_doc['agenda_item_id']:
                solr_doc['agenda_item_id'].append(agenda_item.agenda_item_id)
                solr_doc['agenda_item_title'].append(agenda_item.title.split(":")[-1].strip())
                solr_doc['agenda_item_text'].append(agenda_item.text)

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

        if doc.creation_date is not None:
            solr_doc['creation_date'] = doc.creation_date.strftime(self.DATE_FORMAT),
        if doc.last_modified is not None:
            solr_doc['last_modified'] = doc.last_modified.strftime(self.DATE_FORMAT),
        if doc.last_saved is not None:
            solr_doc['last_saved'] = doc.last_saved.strftime(self.DATE_FORMAT),
        return solr_doc

    def is_solr_doc_outdated(self, solr, doc_id):
        result = solr.search(f"id:{doc_id}", **{"rows": 2147483647, "fl": "version,last_analyzed"})

        if len(result) > 1:
            raise ValueError(f"Expected single document for {doc_id} but found {len(result)}")
        if len(result) == 0:
            return True

        doc = result.docs[0]
        return doc["version"] < self.VERSION

    def handle(self, *args, **options):
        # chunk size
        chunk_size = self.DEFAULT_CHUNK_SIZE
        if options['chunk_size']:
            chunk_size = options['chunk_size']

        total = Document.objects.all().count()
        self.stdout.write(f"Processing {total} documents...")
        processed = 0
        updated = 0

        solr = self._connect_solr()
        solr_docs = []
        for document in Document.objects.all().iterator(chunk_size):
            processed += 1
            if not self.is_solr_doc_outdated(solr, document.id):
                continue

            solr_doc = self._to_solr(document)
            solr_docs.append(solr_doc)
            if len(solr_docs) >= chunk_size:
                solr.add(solr_docs, commit=True)
                updated += len(solr_docs)
                self.stdout.write(f"Submitted {len(solr_docs)} documents to solr. (Processed={processed}/{total})")
                solr_docs = []
        solr.add(solr_docs, commit=True)
        updated += len(solr_docs)
        self.stdout.write(f"Submitted {len(solr_docs)} documents to solr. (Processed={processed}/{total})")
        self.stdout.write(f"{processed} documents processed ({updated} updated).")


