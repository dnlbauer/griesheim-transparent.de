from sqlalchemy import exists

from .models import Person, Organization, Membership, Meeting, Document, AgendaItem, Consultation


class Repository:
    def __init__(self, session):
        self.session = session

    def add_person(self, person):
        session = self.session
        if self.has_person_by_name(person.first_name, person.last_name):
            person.id = self.find_person_by_name(person.first_name, person.last_name).id
        return session.merge(person)

    def get_all_persons(self):
        return self.session.query(Person).all()

    def find_person_by_name(self, first_name, last_name):
        return self.session.query(Person) \
            .filter(Person.last_name.like(last_name)) \
            .filter(Person.first_name.like(first_name)) \
            .one()

    def has_person_by_name(self, first_name, last_name):
        qry = exists(Person).where(
            Person.first_name == first_name,
            Person.last_name == last_name
        )
        return self.session.query(qry).scalar()

    def get_all_organizations(self):
        return self.session.query(Organization).all()

    def add_organization(self, organization):
        session = self.session
        if organization.org_id is not None and self.has_organization_by_org_id(organization.org_id):
            organization.id = self.find_organization_by_org_id(organization.org_id).id
        elif self.has_organization_by_name(organization.name):
            organization.id = self.find_organization_by_name(organization.name).id
        return session.merge(organization)

    def find_organization_by_name(self, name):
        return self.session.query(Organization) \
            .filter(Organization.name == name)\
            .scalar()

    def find_organization_by_org_id(self, org_id):
        return self.session.query(Organization) \
            .filter(Organization.org_id == int(org_id))\
            .scalar()

    def has_organization_by_name(self, name):
        qry = exists(Organization).where(Organization.name == name)
        return self.session.query(qry).scalar()

    def has_organization_by_org_id(self, org_id):
        qry = exists(Organization).where(Organization.org_id == int(org_id))
        return self.session.query(qry).scalar()

    def has_membership(self, organization_id, person_id):
        qry = exists(Membership).where(
            Membership.organization_id == organization_id,
            Membership.person_id == person_id
        )
        return self.session.query(qry).scalar()

    def add_membership(self, membership):
        session = self.session
        if not self.has_membership(membership.organization_id, membership.person_id):
            session.add(membership)
        return self.session.query(Membership) \
            .filter(Membership.organization_id == membership.organization_id) \
            .filter(Membership.person_id == membership.person_id) \
            .one()

    def add_person_with_membership(self, person, organization):
        person = self.add_person(person)
        organization = self.add_organization(organization)
        self.session.flush()
        membership = self.add_membership(
            Membership(person_id=person.id, organization_id=organization.id)
        )
        return person, organization, membership

    def get_all_memberships(self):
        return self.session.query(Membership).all()

    def get_all_meetings(self):
        return self.session.query(Meeting).all()

    def count_all_meetings(self):
        return self.session.query(Meeting.meeting_id).count()

    def has_meeting_by_id(self, meeting_id):
        qry = exists(Meeting).where(
            Meeting.meeting_id == meeting_id
        )
        return self.session.query(qry).scalar()

    def find_meeting_by_id(self, meeting_id):
        return self.session.query(Meeting) \
            .filter(Meeting.meeting_id == meeting_id) \
            .one()

    def add_meeting(self, meeting):
        session = self.session
        if self.has_meeting_by_id(meeting.meeting_id):
            meeting.id = self.find_meeting_by_id(meeting.meeting_id).id
        return session.merge(meeting)

    def get_all_documents(self):
        return self.session.query(Document).all()

    def count_all_documents(self):
        return self.session.query(Document.document_id).count()

    def has_document_by_id(self, document_id):
        qry = exists(Document).where(
            Document.document_id == document_id
        )
        return self.session.query(qry).scalar()

    def find_document_by_id(self, document_id):
        return self.session.query(Document) \
            .filter(Document.document_id == document_id) \
            .one()

    def add_document(self, document):
        session = self.session
        if self.has_document_by_id(document.document_id):
            document.id = self.find_document_by_id(document.document_id).id
        return session.merge(document)

    def add_agenda_item(self, agenda_item):
        session = self.session
        if self.has_agenda_item_by_agenda_item_id(agenda_item.agenda_item_id):
            agenda_item.id = self.find_agenda_item_by_agenda_item_id(agenda_item.agenda_item_id).id
        return session.merge(agenda_item)

    def get_all_agenda_items(self):
        return self.session.query(AgendaItem).all()

    def find_agenda_item_by_agenda_item_id(self, id):
        return self.session.query(AgendaItem) \
            .filter(AgendaItem.agenda_item_id == id) \
            .one()

    def has_agenda_item_by_agenda_item_id(self, id):
        qry = exists(AgendaItem).where(
            AgendaItem.agenda_item_id == id
        )
        return self.session.query(qry).scalar()

    def add_consultation(self, consultation):
        session = self.session
        if self.has_consultation_by_consultation_id(consultation.consultation_id):
            consultation.id = self.find_consultation_by_consultation_id(consultation.consultation_id).id
        return session.merge(consultation)

    def get_all_consultations(self):
        return self.session.query(Consultation).all()

    def find_consultation_by_consultation_id(self, id):
        return self.session.query(Consultation) \
            .filter(Consultation.consultation_id == id) \
            .one()

    def has_consultation_by_consultation_id(self, id):
        qry = exists(Consultation).where(
            Consultation.consultation_id == id
        )
        return self.session.query(qry).scalar()

    def commit(self):
        self.session.commit()
