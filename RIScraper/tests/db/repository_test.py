import pytest

from db import Repository
from db.Schema import Schema
from db.models import Person, Organization, Meeting, Document, AgendaItem, Consultation


@pytest.fixture
def repository():
    schema = Schema("sqlite:///:memory:")
    repository = Repository(schema.create_session())
    yield repository


def test_create_person(repository):
    person = Person(first_name="John", last_name="Doe")
    repository.add_person(person)
    persons = repository.get_all_persons()
    assert len(persons) == 1
    assert persons[0].first_name == "John"


def test_find_person(repository):
    repository.add_person(Person(first_name="John", last_name="Doe"))
    person = repository.find_person_by_name("John", "Doe")
    assert person.first_name == "John"
    assert person.last_name == "Doe"


def test_has_person_by_name(repository):
    repository.add_person(Person(first_name="John", last_name="Doe"))
    assert repository.has_person_by_name("John", "Doe")
    assert not repository.has_person_by_name("Edgar", "Doe")
    assert not repository.has_person_by_name("John", "Bauer")


def test_create_organization(repository):
    organization = Organization(org_id=5, name="test")
    repository.add_organization(organization)
    organizations = repository.get_all_organizations()
    assert len(organizations) == 1
    assert organizations[0].name == "test"


def test_create_orgnization_twice(repository):
    organization = Organization(org_id=5, name="test")
    repository.add_organization(organization)
    organizations = repository.get_all_organizations()
    assert len(organizations) == 1
    assert organizations[0].name == "test"
    repository.session.flush()

    organization = Organization(org_id=5, name="test")
    repository.add_organization(organization)
    organizations = repository.get_all_organizations()
    assert len(organizations) == 1
    assert organizations[0].name == "test"


def test_find_organization(repository):
    repository.add_organization(Organization(org_id=5, name="test"))
    organization = repository.find_organization_by_name("test")
    assert organization.org_id == 5


def test_has_organization_by_name(repository):
    repository.add_organization(Organization(org_id=5, name="test"))
    assert repository.has_organization_by_name("test")
    assert not repository.has_organization_by_name("test2")


def test_add_person_with_membership(repository):
    person = Person(first_name="John", last_name="Doe")
    organization = Organization(org_id=5, name="test")
    person, organization, membership = repository.add_person_with_membership(person, organization)
    repository.session.commit()
    assert membership.person_id == person.id
    assert membership.organization_id == organization.id


def test_add_person_with_membership_existing_person(repository):
    person_old = Person(first_name="John", last_name="Doe")
    repository.add_person(person_old)
    person = Person(first_name="John", last_name="Doe")
    organization = Organization(org_id=5, name="test")
    repository.add_person_with_membership(person, organization)

    assert len(repository.get_all_memberships()) == 1
    assert len(repository.get_all_organizations()) == 1
    assert len(repository.get_all_persons()) == 1


def test_add_person_with_membership_existing_organization(repository):
    organization_old = Organization(org_id=5, name="test")
    repository.add_organization(organization_old)
    repository.session.flush()
    person = Person(first_name="John", last_name="Doe")
    organization = Organization(org_id=5, name="test")
    repository.add_person_with_membership(person, organization)

    assert len(repository.get_all_memberships()) == 1
    assert len(repository.get_all_organizations()) == 1
    assert len(repository.get_all_persons()) == 1


def test_add_person_with_membership_existing_membership(repository):
    person_old = Person(first_name="John", last_name="Doe")
    organization_old = Organization(org_id=5, name="test")
    repository.add_person_with_membership(person_old, organization_old)
    repository.session.flush()
    person = Person(first_name="John", last_name="Doe")
    organization = Organization(org_id=5, name="test")
    repository.add_person_with_membership(person, organization)

    assert len(repository.get_all_memberships()) == 1
    assert len(repository.get_all_organizations()) == 1
    assert len(repository.get_all_persons()) == 1


def test_add_meeting(repository):
    meeting = Meeting(
        meeting_id=5,
        title="This is a very important meeting"
    )
    repository.add_meeting(meeting)
    repository.session.flush()
    assert len(repository.get_all_meetings()) == 1


def test_has_meeting(repository):
    meeting = Meeting(
        meeting_id=5,
        title="Very important meeting"
    )
    repository.add_meeting(meeting)
    repository.session.flush()
    assert repository.has_meeting_by_id(5)
    assert not repository.has_meeting_by_id("6")


def test_find_meeting(repository):
    meeting = Meeting(
        meeting_id=5,
        title="Very important meeting"
    )
    repository.add_meeting(meeting)
    repository.session.flush()
    assert "Very important" in repository.find_meeting_by_id(5).title


def gen_mock_doc():
    return Document(
        document_id=5,
        file_name="Some_file.pdf",
        content_type="application/pdf",
        content_binary=bytes("some byte contet", "utf-8"),
        size=5
    )


def test_add_document(repository):
    document = gen_mock_doc()
    repository.add_document(document)
    repository.session.flush()
    assert len(repository.get_all_documents()) == 1


def test_has_document(repository):
    document = gen_mock_doc()
    repository.add_document(document)
    repository.session.flush()
    assert repository.has_document_by_id(5)
    assert not repository.has_document_by_id("6")


def test_find_document(repository):
    document = gen_mock_doc()
    repository.add_document(document)
    repository.session.flush()
    assert "Some_file" in repository.find_document_by_id(5).file_name


def gen_agenda_item_mock():
    return AgendaItem(
        agenda_item_id=5,
        title="test",
        decision="test decision",
        vote="X: 5",
    )


def test_add_agenda_item(repository):
    item = gen_agenda_item_mock()
    repository.add_agenda_item(item)
    repository.session.flush()
    assert(repository.find_agenda_item_by_agenda_item_id(5).title == "test")


def test_get_all_agenda_items(repository):
    item = gen_agenda_item_mock()
    repository.add_agenda_item(item)
    repository.session.flush()
    assert(len(repository.get_all_agenda_items()) == 1)


def test_find_agenda_item(repository):
    item = gen_agenda_item_mock()
    repository.add_agenda_item(item)
    repository.session.flush()
    assert(repository.find_agenda_item_by_agenda_item_id(5).title == "test")


def test_has_agenda_item(repository):
    item = gen_agenda_item_mock()
    repository.add_agenda_item(item)
    repository.session.flush()
    assert(repository.has_agenda_item_by_agenda_item_id(5))


def gen_consultation_mock():
    return Consultation(
        consultation_id=5,
        name="Test/2022/005",
        topic="test topic",
        type="Antragsvorlage"
    )


def test_add_consultation(repository):
    item = gen_consultation_mock()
    repository.add_consultation(item)
    repository.session.flush()
    assert(repository.find_consultation_by_consultation_id(5).name == "Test/2022/005")
    item2 = gen_consultation_mock()
    repository.add_consultation(item2)
    repository.session.flush()
    assert(len(repository.get_all_consultations()) == 1)


def test_get_all_consultations(repository):
    item = gen_consultation_mock()
    repository.add_consultation(item)
    repository.session.flush()
    assert(len(repository.get_all_consultations()) == 1)


def test_find_consultation(repository):
    item = gen_consultation_mock()
    repository.add_consultation(item)
    repository.session.flush()
    assert(repository.find_consultation_by_consultation_id(5).name == "Test/2022/005")


def test_has_consultation(repository):
    item = gen_consultation_mock()
    repository.add_consultation(item)
    repository.session.flush()
    assert(repository.has_consultation_by_consultation_id(5))
