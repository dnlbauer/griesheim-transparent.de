import tika
from datetime import datetime
import re

import pysolr
from django.core.management import BaseCommand

from frontend import settings
from ris.management.utils import get_preview_image_for_doc, analyze_document_pdfact, analyze_document_tika
from frontend.models.risdb import Document, Organization

# Force tika to use an external service
tika.TikaClientOnly = True

class Command(BaseCommand):
    help = "Update solr index from risdb"

    DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    DEFAULT_CHUNK_SIZE = 10  # chunk size for solr document commiting
    VERSION = 4  # incr. if analyze chain changes to force a full resync

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
        # find associated consultations, meetings, ..

        consultations = doc.consultations.all()
        consultation = None
        if len(consultations) > 1:
            raise ValueError("Associated consultation objects > 1. This is unexpected")
        elif len(consultations) == 1:
            consultation = consultations[0]

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

        return consultation, meetings, agenda_items


    def _parse_solr_document(self, doc, tika_result, pdfact_result, preview_image):
        solr_doc = dict(
            id=str(doc.id),
            version=self.VERSION,
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

        for meeting in meetings:
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

        # add content strings from tika/pdfact
        def clean_string(s):
            return re.sub(r"\s+", " ", s).strip()

        # pdfact has data nicely seperated into chunks.
        # prefered over unordered tika content
        if pdfact_result is not None:
            solr_doc["content"] = [clean_string(s) for s in pdfact_result]
        elif tika_result is not None and "content" in tika_result and tika_result["content"]:
            solr_doc["content"] = [tika_result["content"]]


        # parse metadata from tika
        def get_metadata(metadata, fields):
            for i in fields:
                if i in metadata:
                    return metadata[i]

        if tika_result is not None:
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
                print("!! Invalid organization skipped: {org} !!")
        return checked_organizations


    def _is_solr_doc_outdated(self, solr, doc_id):
        result = solr.search(f"id:{doc_id}", **{"rows": 2147483647, "fl": "version,last_analyzed"})

        if len(result) > 1:
            raise ValueError(f"Expected single document for {doc_id} but found {len(result)}")
        if len(result) == 0:
            return True

        doc = result.docs[0]
        return doc["version"] < self.VERSION


    def handle(self, *args, **options):
        # get command arguments
        chunk_size = self.DEFAULT_CHUNK_SIZE
        if options['chunk_size']:
            chunk_size = options['chunk_size']
        force = options["force"]
        ocr = options["no_ocr"]

        self._log(f"Processing {Document.objects.all().count()} documents...")
        processed = 0
        updated = 0

        solr = pysolr.Solr(f"{settings.SOLR_HOST}/{settings.SOLR_COLLECTION}")
        solr_docs = []

        # filter document ids for outdated documents
        document_ids = Document.objects.values_list("id", flat=True)
        document_ids = [i for i in document_ids if force or self._is_solr_doc_outdated(solr, i)]
        total = len(document_ids)
        self._log(f"Outdated documents: {total}")

        for document_id in document_ids:
            document = Document.objects.get(id=document_id)
            processed += 1

            # filter non-pdfs
            if not document.content_type.lower().endswith("pdf"):
                self._log(f"Skipped {document.file_name} (no pdf) ({str(document.id)})")
                continue

            self._log(f"Processing {document.file_name} ({str(document.id)})")

            # analyze document with tika
            self._log("Sending document to tika")
            tika_result = analyze_document_tika(document.content_binary, False)

            # Run OCR/tesseract if there is no content from tika without ocr
            if ocr and (tika_result is None or tika_result["content"] is None or len(tika_result["content"]) == 0):
                self._log("Sending document to tika/ocr")
                tika_result = analyze_document_tika(document.content_binary, True)

            # run pdfact
            self._log("Sending document to pdfact")
            pdfact_result = analyze_document_pdfact(document.content_binary)

            # get preview thumbnail
            self._log("Sending document to preview service")
            preview_image = get_preview_image_for_doc(document.document_id)

            # generate solr document from data
            self._log("Creating solr document")
            solr_doc = self._parse_solr_document(document, tika_result, pdfact_result, preview_image)
            solr_docs.append(solr_doc)

            # write chunks to solr
            if len(solr_docs) >= chunk_size:
                self._log(f"Submitting {len(solr_docs)} documents to solr. (Processed={processed}/{total})")
                solr.add(solr_docs, commit=True)
                updated += len(solr_docs)
                solr_docs = []

        # commit last incomplete chunk
        solr.add(solr_docs, commit=True)
        updated += len(solr_docs)
        self._log(f"Submitting {len(solr_docs)} documents to solr. (Processed={processed}/{total})")

        self._log(f"{processed} documents processed ({updated} updated).")


