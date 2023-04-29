import os

import tika
from datetime import datetime
import re

import pysolr
from django.core.management import BaseCommand

from frontend import settings
from frontend.management.utils import get_preview_image_for_doc, analyze_document_pdfact, analyze_document_tika
from ris.models import Organization, Document

# Force tika to use an external service
tika.TikaClientOnly = True


class Command(BaseCommand):
    help = "Update solr index from risdb"

    DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    DEFAULT_CHUNK_SIZE = 10  # chunk size for solr document commit

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

    def _log(self, message):
        self.stdout.write(message)

    def _get_relevant_events(self, doc):
        """ Returns a list of consultations, meetings, agenda_items relevant
        for this document """

        consultation = doc.consultation_set.first()
        meetings = set(doc.meeting_set.all())
        agenda_items = set(doc.agendaitem_set.all())

        # addend agenda items belonging to this consultation
        if consultation is not None:
            consultation_agenda_items = consultation.agendaitem_set.all()
            for item in consultation_agenda_items:
                agenda_items.add(item)
                meetings.add(item.meeting)
            consultation_meetings = consultation.meeting_set.all()
            for item in consultation_meetings:
                meetings.add(item)

        return consultation, meetings, agenda_items

    def _parse_solr_document(self, doc, content, metadata, preview_image):
        solr_doc = dict(
            id=str(doc.id),
            last_analyzed=datetime.now().strftime(self.DATE_FORMAT),
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
            preview_image=preview_image,
            content=[]
        )

        # include data from associated events
        consultation, meetings, agenda_items = self._get_relevant_events(doc)

        if consultation is not None:
            solr_doc["consultation_id"] = consultation.consultation_id
            solr_doc["consultation_name"] = consultation.name
            solr_doc["consultation_type"] = consultation.type
            solr_doc["consultation_text"] = consultation.text
            solr_doc['doc_type'] = consultation.type

            # find antragssteller for consultations
            found = re.search(r'\"?(.*?)\"?,?\s(Gemeinsamer\s)?Antrag (der|des) (.*)', consultation.topic)
            if found:
                title, organizations = found.group(1), found.group(4)
                solr_doc["consultation_topic"] = title
                organizations = self._parse_consultation_organization(organizations)
                solr_doc["consultation_organization"] = organizations
            else:
                solr_doc["consultation_topic"] = consultation.topic

        for agenda_item in agenda_items:
            solr_doc['agenda_item_id'].append(agenda_item.agenda_item_id)
            solr_doc['agenda_item_title'].append(agenda_item.title.split(":")[-1].strip())
            solr_doc['agenda_item_text'].append(agenda_item.text)

        last_seen = None
        first_seen = None
        for meeting in meetings:
            solr_doc['meeting_id'].append(meeting.meeting_id)
            solr_doc['meeting_title'].append(meeting.title)
            solr_doc['meeting_title_short'].append(meeting.title_short)
            solr_doc['meeting_date'].append(meeting.date.strftime(self.DATE_FORMAT))
            solr_doc['meeting_organization_name'].append(meeting.organization.name)
            if last_seen is None or last_seen < meeting.date:
                last_seen = meeting.date
            if first_seen is None or first_seen > meeting.date:
                first_seen = meeting.date

        if last_seen is not None:
            solr_doc['last_seen'] = last_seen.strftime(self.DATE_FORMAT)
        if first_seen is not None:
            solr_doc['first_seen'] = first_seen.strftime(self.DATE_FORMAT)

        solr_doc['meeting_count'] = len(solr_doc['meeting_id'])

        # add content strings from tika/pdfact
        solr_doc["content"] = [re.sub(r"\s+", " ", s).strip() for s in content]

        def get_metadata_value(metadata, fields):
            for i in fields:
                if i in metadata:
                    return metadata[i]

        if metadata is not None:
            author = get_metadata_value(metadata,  ["Author", "creator", "dc:creator", "meta:author", "pdf:docinfo:creator"])
            if author is not None:
                solr_doc["author"] = author

            creation_date = get_metadata_value(metadata, ["Creation-Date", "created", "dcterms:created", "meta:creation-date", "pdf:docinfo:created"])
            if creation_date is not None:
                solr_doc['creation_date'] = creation_date

            last_modified = get_metadata_value(metadata, ["Last-Modified", "dcterms:modified", "modified", "pdf:docinfo:modified"])
            if last_modified is not None:
                solr_doc['last_modified'] = last_modified

            last_save_date = get_metadata_value(metadata, ["Last-Save-Date", "meta:save-date"])
            if last_save_date is not None:
                solr_doc['last_saved'] = last_save_date

        # Niederschrift type recognized by keyword "Niederschrift" title
        if 'doc_type' not in solr_doc or solr_doc['doc_type'] is None:
            if "niederschrift" in doc.title.lower():
                solr_doc['doc_type'] = "Niederschrift"

        return solr_doc

    def _parse_consultation_organization(self, organizations):
        # SPD-Fraktion -> SPD
        # Fraktionen CDU, SPD und B90/Die Grünen -> CDU, SPD, B90/Die Grünen
        organizations = re.sub(r'\-?Fraktion(en)?\s*', "", organizations).replace(" und ", ", ")
        organizations = [org.strip() for org in organizations.split(",")]
        replacements = [
            (r"Bürgermeister.*", "Bürgermeister"),
            (r".*Grüne.*", "B90/Grüne"),
            (r"Seniorenbeirat.*", "Seniorenbeirat"),
            (r"Ausländerbeirat.*", "Ausländerbeirat"),
            (r"Stadtverwaltung.*", "Stadtverwaltung Griesheim"),

        ]
        for replacement in replacements:
            organizations = [re.sub(*replacement, org) for org in organizations]

        checked_organizations = []
        for org in organizations:
            if Organization.objects.filter(name=org).count() == 1:
                checked_organizations.append(org)
            else:
                self._log(f"!! Invalid organization skipped: {org} !!")
        return checked_organizations

    def handle(self, *args, **options):
        # get command arguments
        chunk_size = self.DEFAULT_CHUNK_SIZE
        if options['chunk_size']:
            chunk_size = options['chunk_size']
        force = options["force"]
        ocr = options["no_ocr"]

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
            if document.content_type.lower().endswith("pdf"):  # TODO convert non-pdfs for analysis
                file_path = os.path.join(settings.DOCUMENT_STORE, document.uri)

                self._log("Sending document to pdfact")
                content = analyze_document_pdfact(file_path, skip_cache=force)

                # analyze document with tika
                self._log("Sending document to tika")
                tika_result = analyze_document_tika(file_path, False, skip_cache=force)

                # Run OCR/tesseract if there is no content from tika without ocr
                if ocr and (tika_result is None or tika_result["content"] is None or len(tika_result["content"]) == 0):
                    self._log("Sending document to tika/ocr")
                    tika_result = analyze_document_tika(file_path, True, skip_cache=force)
                metadata = tika_result["metadata"]
                if content is None or len(content) == 0:
                    content = tika_result["content"]

                self._log("Sending document to preview service")
                preview_image = get_preview_image_for_doc(file_path, skip_cache=force)

            # generate solr document from data
            solr_doc = self._parse_solr_document(document, content, metadata, preview_image)
            solr_docs.append(solr_doc)
            processed += 1

            # write chunks to solr
            if len(solr_docs) >= chunk_size:
                self._log(f"Submitting {len(solr_docs)} documents to solr. (Processed={processed}/{total})")
                solr.add(solr_docs, commit=True)
                solr_docs = []

        # commit last incomplete chunk
        solr.add(solr_docs, commit=True)
        self._log(f"Submitting {len(solr_docs)} documents to solr. (Processed={processed}/{total})")
        self._log(f"Processed {processed} documents.")

