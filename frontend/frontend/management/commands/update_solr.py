import tika
from datetime import datetime
import re

import pysolr
from django.core.management import BaseCommand

from frontend import settings
from frontend.risdb.models import Document
from frontend.utils import get_preview_image_for_doc, analyze_document_tika

tika.TikaClientOnly = True

class Command(BaseCommand):
    help = "Update solr from risdb"

    DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    DEFAULT_CHUNK_SIZE = 10
    VERSION = 2  # incr. if analyze chain changes

    def add_arguments(self, parser):
        parser.add_argument("--chunk_size",
                            help=f"chunk size for document processing (default: {self.DEFAULT_CHUNK_SIZE})",
                            type=int)
        parser.add_argument("--force",
                            help="force update for all documents",
                            action="store_true")
        parser.add_argument("--no-ocr",
                            help="allow ocr for documents (takes a long time)",
                            action="store_false")

    def log(self, message):
        self.stdout.write(message)

    def _connect_solr(self):
        solr = pysolr.Solr(f"{settings.SOLR_HOST}/{settings.SOLR_COLLECTION}")
        return solr

    def _to_solr(self, doc, tika_result, preview_image):
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
            preview_image=preview_image
        )

        if consultation is not None:
            solr_doc["consultation_id"] = consultation.consultation_id
            solr_doc["consultation_name"] = consultation.name
            solr_doc["consultation_topic"] = consultation.topic
            solr_doc["consultation_type"] = consultation.type
            solr_doc["consultation_text"] = consultation.text
            solr_doc['doc_type'] = consultation.type

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

        # add data from tika
        def clean_string(s):
            return re.sub(r"\s+", " ", s).strip()

        def get_metadata(metadata, fields):
            for i in fields:
                if i in metadata:
                    return metadata[i]

        # parse data from tika
        if tika_result is not None:
            if tika_result["content"] is not None:
                solr_doc["content"] = clean_string(tika_result["content"])

            metadata = tika_result["metadata"]
            author = get_metadata(metadata,  ["Author", "creator", "dc:creator", "meta:author", "pdf:docinfo:creator"])
            if author is not None:
                solr_doc["author"] = author

            creation_date = get_metadata(metadata, ["Creation-Date", "created", "dcterms:created", "meta:creation-date", "pdf:docinfo:created"])
            if creation_date is not None:
                solr_doc['creation_date'] = creation_date

            last_modified = get_metadata(metadata, ["Last-Modified", "dcterms:modified", "modified", "pdf:docinfo:modified"])
            if last_modified is not None:
                solr_doc['last_modified'] = last_modified

            last_save_date = get_metadata(metadata, ["Last-Save-Date", "meta:save-date"])
            if last_save_date is not None:
                solr_doc['last_saved'] = last_save_date


        # Niederschrift recognized by keyword "Niederschrift" in content or title
        if 'doc_type' not in solr_doc or solr_doc['doc_type'] is None:
            if solr_doc["content"] and ("niederschrift" in solr_doc["content"][:100].lower() or "niederschrift" in doc.title.lower()):
                solr_doc['doc_type'] = "Niederschrift"


        return solr_doc

    def _is_solr_doc_outdated(self, solr, doc_id):
        result = solr.search(f"id:{doc_id}", **{"rows": 2147483647, "fl": "version,last_analyzed"})

        if len(result) > 1:
            raise ValueError(f"Expected single document for {doc_id} but found {len(result)}")
        if len(result) == 0:
            return True

        doc = result.docs[0]
        return doc["version"] < self.VERSION


    def handle(self, *args, **options):
        # get arguments
        chunk_size = self.DEFAULT_CHUNK_SIZE
        if options['chunk_size']:
            chunk_size = options['chunk_size']
        force = options["force"]
        ocr = options["no_ocr"]

        total = Document.objects.all().count()
        self.log(f"Processing {total} documents...")
        processed = 0
        updated = 0

        solr = self._connect_solr()
        solr_docs = []
        for document in Document.objects.all().iterator():
            processed += 1

            # skip document if outdated
            if not (force or self._is_solr_doc_outdated(solr, document.id)):
                continue

            # filter non-pdfs
            if not document.content_type.lower().endswith("pdf"):
                self.log(f"Skipped {document.file_name} (no pdf) ({str(document.id)}")
                continue

            self.log(f"Processing {document.file_name} ({str(document.id)})")

            # analyze document with tika
            self.log("Sending document to tika")
            tika_result = analyze_document_tika(document.content_binary, False)

            # Only run OCR/tesseract if there is no content from tika w/o ocr
            if ocr and (tika_result is None or tika_result["content"] is None or len(tika_result["content"]) == 0):
                self.log("Sending document to tika/ocr")
                tika_result = analyze_document_tika(document.content_binary, True)

            # get preview image
            self.log("Sending document to preview service")
            preview_image = get_preview_image_for_doc(document.document_id)

            # generate solr document from data
            self.log("Creating solr document")
            solr_doc = self._to_solr(document, tika_result, preview_image)
            solr_docs.append(solr_doc)

            # write chunks to solr
            if len(solr_docs) >= chunk_size:
                solr.add(solr_docs, commit=True)
                updated += len(solr_docs)
                self.log(f"Submitted {len(solr_docs)} documents to solr. (Processed={processed}/{total})")
                solr_docs = []

        solr.add(solr_docs, commit=True)
        updated += len(solr_docs)
        self.log(f"Submitted {len(solr_docs)} documents to solr. (Processed={processed}/{total})")
        self.log(f"{processed} documents processed ({updated} updated).")


