import re
from datetime import datetime

from ris.models import Organization

SOLR_DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def get_relevant_events(doc):
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


def parse_solr_document(doc, content, metadata, preview_image):
    solr_doc = dict(
        id=str(doc.id),
        last_analyzed=datetime.now().strftime(SOLR_DATE_FORMAT),
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
    consultation, meetings, agenda_items = get_relevant_events(doc)

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
            organizations = parse_consultation_organization(organizations)
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
        solr_doc['meeting_date'].append(meeting.date.strftime(SOLR_DATE_FORMAT))
        solr_doc['meeting_organization_name'].append(meeting.organization.name)
        if last_seen is None or last_seen < meeting.date:
            last_seen = meeting.date
        if first_seen is None or first_seen > meeting.date:
            first_seen = meeting.date

    if last_seen is not None:
        solr_doc['last_seen'] = last_seen.strftime(SOLR_DATE_FORMAT)
    if first_seen is not None:
        solr_doc['first_seen'] = first_seen.strftime(SOLR_DATE_FORMAT)

    solr_doc['meeting_count'] = len(solr_doc['meeting_id'])

    # add content strings from tika/pdfact
    if content is not None:
        solr_doc["content"] = [re.sub(r"\s+", " ", s).strip() for s in content]

    def get_metadata_value(metadata, fields):
        for i in fields:
            if i in metadata:
                return metadata[i]

    if metadata is not None:
        author = get_metadata_value(metadata, ["Author", "creator", "dc:creator", "meta:author", "pdf:docinfo:creator"])
        if author is not None:
            solr_doc["author"] = author

        creation_date = get_metadata_value(metadata,
                                           ["Creation-Date", "created", "dcterms:created", "meta:creation-date",
                                            "pdf:docinfo:created"])
        if creation_date is not None:
            solr_doc['creation_date'] = creation_date

        last_modified = get_metadata_value(metadata,
                                           ["Last-Modified", "dcterms:modified", "modified", "pdf:docinfo:modified"])
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


def parse_consultation_organization(organizations):
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
            print(f"!! Invalid organization skipped: {org} !!")
    return checked_organizations
