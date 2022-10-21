import multiprocessing
from multiprocessing import Queue

import pytest

from Scraper import scrape_persons, scrape_organization, scrape_organizations, init_queue_meetings_calendar, \
    scrape_calendar_month, scrape_meeting, scrape_document, scrape_agenda_item, download_document, scrape_consultation, \
    init_queue_with_drafts
from db import Repository
from db.Schema import Schema
from db.models import Person, Organization, Document, Consultation
from utils import parse_config_and_args


@pytest.fixture
def db():
    return Schema("sqlite:///:memory:")

@pytest.fixture
def config():
    return parse_config_and_args("../config.yaml", None)

@pytest.fixture
def queue():
    return Queue()

@pytest.fixture
def lock():
    return multiprocessing.Lock()


def test_scrape_persons(db, config, lock):
    scrape_persons(db, config, lock)
    session = db.create_session()
    assert (session.query(Person.id).count() > 50)
    test_person = Repository(session).find_person_by_name("Jörg", "Prattinger")
    assert (test_person)
    assert (len(test_person.memberships) == 1)


def test_scrape_organizations(config, queue):
    scrape_organizations(config, queue)
    assert(queue.qsize() > 5)


def test_scrape_organization(config, db, lock):
    scrape_organization(1, config, db, lock)  # stadtverordnetenversammlung
    session = db.create_session()
    assert (session.query(Organization.id).count() == 1)
    test_organization = Repository(session).find_organization_by_name("Stadtverordnetenversammlung")
    assert (len(test_organization.memberships) > 10)


def test_init_calendar_queue(queue):
    start_month = 5
    start_year = 2010
    end_month = 6
    end_year = 2011
    init_queue_meetings_calendar(start_month, start_year, end_month, end_year, queue)
    assert(queue.qsize() == 8+6)
    assert(queue.get().id == (5, 2010))


def test_scrape_calendar_month(config, queue):
    scrape_calendar_month(4, 2022, config, queue)
    assert(queue.qsize() == 2)
    ids = [queue.get().id, queue.get().id]
    assert("5742" in ids)
    assert("6747" in ids)


def test_scrape_meeting(config, db, queue, lock):
    session = db.create_session()
    Repository(session).add_organization(Organization(org_id=1, name="Wirtschafts- und Finanzausschuss"))
    session.commit()
    scrape_meeting(8825, config, db, queue, lock)

    meeting = Repository(db.create_session()).get_all_meetings()[0]
    assert (meeting.meeting_id == 8825)
    assert ("Wirtschafts- und Finanzausschuss" in meeting.title)
    assert (meeting.title_short == "WF/2022/0013")
    assert (meeting.date is not None)
    expected_organization_id = db.create_session().query(
        Organization.id
    ).limit(1).one()[0]
    assert (meeting.organization_id == expected_organization_id)

    # assert documents are scraped with their respective title and are associated with the meeting
    document = Repository(db.create_session()).find_document_by_id(44130)
    assert(document.title == "Sachstand Digitalisierung")

    # documents from main should be associated with meeting
    documents = meeting.documents
    has_doc = False
    for doc in documents:
        if doc.document_id == 44130:
            has_doc = True
    assert(has_doc)

    # consultations should be associated with meeting
    consultations = meeting.consultations
    assert(len(consultations) == 9)
    has_consultation = False
    for consultation in consultations:
        print(consultation.name)
        if "AG/2022/0064" in consultation.name:
            has_consultation = True
    assert(has_consultation)


def test_download_document(config):
    doc = download_document(38940, config)
    assert (doc.document_id == 38940)
    assert (doc.file_name == "Niederschrift_STVV.pdf")
    assert (doc.content_type.lower() == "application/pdf")
    assert (doc.size > 10)


def test_scrape_document(config, db, queue, lock):
    scrape_document(38940, config, db, queue, lock)
    with db.create_session() as s:
        assert (s.query(Document.id).count() == 1)


def test_scrape_document_exists(config, db, queue, lock):
    """ should not re-download existing document """
    scrape_document(38940, config, db, queue, lock)
    scrape_document(38940, config, db, queue, lock)
    with db.create_session() as s:
        assert (s.query(Document.id).count() == 1)


def test_scrape_agenda_item_empty(config, db, queue, lock):
    scrape_agenda_item(33520, config, db, queue, lock)
    item = Repository(db.create_session()).get_all_agenda_items()[0]
    assert (item.agenda_item_id == 33520)
    assert ("Mitteilungen der Stadtverordnetenvorsteherin" in item.title)
    assert (item.decision is None)
    assert (item.vote is None)
    assert (item.text is None)


def test_scrape_agenda_item_exists(config, db, queue, lock):
    scrape_agenda_item(33520, config, db, queue, lock)
    scrape_agenda_item(33520, config, db, queue, lock)
    assert (len(Repository(db.create_session()).get_all_agenda_items()) == 1)
    item = Repository(db.create_session()).get_all_agenda_items()[0]
    assert (item.agenda_item_id == 33520)
    assert ("Mitteilungen der Stadtverordnetenvorsteherin" in item.title)
    assert (item.decision is None)
    assert (item.vote is None)
    assert (item.text is None)


def test_scrape_agenda_item_text(config, db, queue, lock):
    scrape_agenda_item(33532, config, db, queue, lock)
    item = Repository(db.create_session()).get_all_agenda_items()[0]
    assert (item.decision == "einstimmig beschlossen")
    assert (item.text.startswith("Im Zeitraum vom"))
    assert (item.text.endswith("Die genaue Erstattungsregelung wird durch den Magistrat festgelegt."))


def test_scrape_agenda_item_voting(config, db, queue, lock):
    scrape_agenda_item(33529, config, db, queue, lock)
    item = Repository(db.create_session()).get_all_agenda_items()[0]
    assert (item.decision == "mehrheitlich beschlossen")
    assert (item.vote == "Ja: 17, Nein: 5, Enthaltungen: 10")
    assert (item.text == "Die vorliegende Geschäftsordnung der Stadtverordnetenversammlung und der Ausschüsse der Stadt Griesheim wird beschlossen.")


def test_scrape_agenda_documents(config, db, queue, lock):
    with db.create_transaction() as t:
        repo = Repository(t.session)
        repo.add_document(Document(
            document_id=5,
            file_name="test",
            content_binary=bytes("qwert", "utf-8"),
            size=5
        ))
    scrape_agenda_item(33609, config, db, queue, lock)
    item = Repository(db.create_session()).get_all_agenda_items()[0]
    assert (len(item.documents) == 1)


def test_scrape_agenda_item_vorlage(config, db, queue, lock):
    with db.create_session() as s:
        id = Repository(s).add_consultation(Consultation(
            consultation_id=14066,
            topic="Lokale Stromspeicher",
            name="AG/2022/0058"
        )).id
    scrape_agenda_item(33609, config, db, queue, lock)
    item = Repository(db.create_session()).get_all_agenda_items()[0]
    assert (item.decision == "einstimmig beschlossen")
    assert (item.consultation_id == id)


def test_scrape_agenda_item_vorlage_not_exist_yet(config, db, queue, lock):
    scrape_agenda_item(33609, config, db, queue, lock)
    item = Repository(db.create_session()).get_all_agenda_items()[0]
    assert (item.consultation_id is not None)


def test_scrape_consultation(config, db, queue, lock):
    scrape_consultation(12966, config, db, queue, lock)
    item = Repository(db.create_session()).get_all_consultations()[0]
    assert (item.consultation_id == 12966)
    assert (item.name == "AG/2022/0051")
    assert (item.type == "Antragsvorlage")
    assert ("Die lokale Energiewende" in item.topic)
    assert (len(item.documents) == 3)
    document_titles = [doc.title for doc in item.documents]
    assert("AG 2022 0051" in document_titles)
    assert("ÄAG 2022 0051 B90" in document_titles)



def test_scrape_consultation_exists(config, db, queue, lock):
    scrape_consultation(12966, config, db, queue, lock)
    scrape_consultation(12966, config, db, queue, lock)
    assert (len(Repository(db.create_session()).get_all_consultations()) == 1)
    item = Repository(db.create_session()).get_all_consultations()[0]
    assert (item.consultation_id == 12966)
    assert (item.name == "AG/2022/0051")
    assert (item.type == "Antragsvorlage")
    assert ("Die lokale Energiewende" in item.topic)
    assert (len(item.documents) == 3)


def test_scrape_consultation_with_text(config, db, queue, lock):
    scrape_consultation(12822, config, db, queue, lock)
    item = Repository(db.create_session()).get_all_consultations()[0]
    assert (item.consultation_id == 12822)
    assert (item.name == "BV/2021/0316")
    assert (item.type == "Beschlussvorlage")
    assert ("Wahl einer in der Altenarbeit besonders erfahrenen Person" in item.topic)
    assert (item.text.startswith("Als in der Altenarbeit besonders erfahrene"))
    assert (len(item.documents) == 1)


def test_init_queue_with_drafts(config, queue):
    init_queue_with_drafts(config, queue)
    assert(queue.qsize() > 1)

