import os

import scrapy.pipelines.files
from itemadapter import ItemAdapter

from peewee import *
from sessionnet.items import OrganizationItem, MeetingItem, DocumentItem, ConsultationItem, AgendaItem
from sessionnet.utils import get_url_params


class HTMLFilterPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        for field in adapter.field_names():
            value = adapter.get(field)
            if value and isinstance(value, str):
                # remove non-breakable space
                value = value.replace(u"\xa0", " ")
            adapter[field] = value
        return item


class MyFilesPipeline(scrapy.pipelines.files.FilesPipeline):

    def file_path(self, request, response=None, info=None, *, item=None):
        file_id = get_url_params(request.url)["id"]
        ending = ItemAdapter(item).get("file_name").split(".")[-1]
        return f"{file_id}.{ending}"


class PsqlExportPipeline:
    def open_spider(self, spider):
        spider.logger.info("Opening database connection")
        db = PostgresqlDatabase(
            spider.settings.get("DB_NAME"),
            user=spider.settings.get("DB_USER"),
            password=spider.settings.get("DB_PASSWORD"),
            host=spider.settings.get("DB_HOST"),
            port=spider.settings.get("DB_PORT"))
        self.db = db
        self.Person = Table("persons", ("id", "person_id", "name")).bind(db)
        self.Organization = Table("organizations", ("id", "organization_id", "name")).bind(db)
        self.Membership = Table("memberships", ("id", "person_id", "organization_id", "from_date", "to_date")).bind(db)
        self.Meeting = Table("meetings", ("id", "meeting_id", "title", "title_short", "date", "organization_id", "organization_name")).bind(db)
        self.Consultation = Table("consultations", ("id", "consultation_id", "name", "topic", "type", "text")).bind(db)
        self.AgendaItem = Table("agendaitems", ("id", "agenda_item_id", "title", "decision", "vote", "text", "consultation_id", "meeting_id")).bind(db)
        self.Document = Table("documents", ("id", "document_id", "file_name", "content_type", "content_binary", "size", "title")).bind(db)
        self.Meeting_Document = Table("meetings_documents", ("id", "meeting_id", "document_id")).bind(db)
        self.Meeting_Consultation = Table("meetings_consultations", ("id", "meeting_id", "consultation_id")).bind(db)

        self.meetings_organizations = []
        self.meetings_documents = []
        self.meetings_consultations = []
        self.agenda_item_meetings = []
        self.consultations_documents = []
        self.consultations_agend_items = []

    def close_spider(self, spider):
        spider.logger.info("Closing database connection")

    def process_item(self, item, spider):
        if isinstance(item, OrganizationItem):
            self.process_organization(item, spider)
        elif isinstance(item, MeetingItem):
            self.process_meeting(item, spider)
        elif isinstance(item, ConsultationItem):
            self.process_consultations(item, spider)
        elif isinstance(item, AgendaItem):
            self.process_agenda_item(item, spider)
        elif isinstance(item, DocumentItem):
            self.process_document(item, spider)
        return item

    def process_meeting(self, item, spider):
        self.Meeting.insert({
            self.Meeting.meeting_id: item.get('id'),
            self.Meeting.title: item.get("title"),
            self.Meeting.title_short: item.get("title_short"),
            self.Meeting.date: item.get("date"),
        }).on_conflict(
            conflict_target=self.Meeting.meeting_id,
            action="update",
            update={
                self.Meeting.title: item.get("title"),
                self.Meeting.title_short: item.get("title_short"),
                self.Meeting.date: item.get("date"),
            }
        ).execute()
        self.meetings_organizations.append((item.get('id'), item.get("organization")))
        self.meetings_documents += (item.get("id"), item.get("file_ids"))
        self.meetings_consultations += (item.get("id", item.get("consultation_ids")))

    def process_consultations(self, item, spider):
        self.Consultation.insert({
            self.Consultation.consultation_id: item.get("id"),
            self.Consultation.name: item.get("name"),
            self.Consultation.topic: item.get("topic"),
            self.Consultation.type: item.get("type"),
            self.Consultation.text: item.get("text")
        }).on_conflict(
            conflict_target=self.Consultation.consultation_id,
            action="update",
            update={
                self.Consultation.name: item.get("name"),
                self.Consultation.topic: item.get("topic"),
                self.Consultation.type: item.get("type"),
                self.Consultation.text: item.get("text")
            }
        ).execute()
        self.consultations_documents += (item.get("id"), item.get("file_ids"))
        self.consultations_agend_items += (item.get("id"), item.get("agenda_ids"))

    def process_agenda_item(self, item, spider):
        self.AgendaItem.insert({
            self.AgendaItem.agenda_item_id: item.get("id"),
            self.AgendaItem.title: item.get("title"),
            self.AgendaItem.decision: item.get("decision"),
            self.AgendaItem.vote: item.get("vote"),
            self.AgendaItem.text: item.get("text"),
        }).on_conflict(
            conflict_target=self.AgendaItem.agenda_item_id,
            action="update",
            update={
                self.AgendaItem.title: item.get("title"),
                self.AgendaItem.decision: item.get("decision"),
                self.AgendaItem.vote: item.get("vote"),
                self.AgendaItem.text: item.get("text"),
            }
        ).execute()

    def process_document(self, item, spider):
        path = os.path.join(spider.settings.get("FILES_STORE"), item.get("files")[0].get("path"))
        size = os.path.getsize(path)
        content = "test" ## TODO get content binary

        self.Document.insert({
            self.Document.document_id: item.get("id"),
            self.Document.file_name: item.get("file_name"),
            self.Document.content_type: item.get("content_type"),
            self.Document.content_binary: content,
            self.Document.size: size,
            self.Document.title: item.get("title")
        }).on_conflict(
            conflict_target=self.Document.document_id,
            action="update",
            update={
                self.Document.file_name: item.get("file_name"),
                self.Document.content_type: item.get("content_type"),
                self.Document.content_binary: content,
                self.Document.size: size,
                self.Document.title: item.get("title")
            }
        ).execute()

    def process_organization(self, item, spider):
        self.db.begin()
        self.Organization.insert({
            self.Organization.organization_id: item.get("id"),
            self.Organization.name: item.get("title")
        }).on_conflict(
            conflict_target=self.Organization.organization_id,
            action="update",
            update={self.Organization.name: item.get("title")}
        ).execute()
        organization_id = self.Organization.select(self.Organization.id).where(self.Organization.organization_id == item.get('id')).first().get('id')

        for person in item.get("persons"):
            self.Person.insert({
                self.Person.person_id: person.get("id"),
                self.Person.name: person.get("name"),
            }).on_conflict(
                conflict_target=self.Person.name,
                action="update",
                update={self.Person.name: person.get("name")}
            ).execute()
            person_id = self.Person.select(self.Person.id).where(self.Person.name == person.get("name")).first().get("id")
            self.Membership.insert({
                self.Membership.person_id: person_id,
                self.Membership.organization_id: organization_id,
                self.Membership.from_date: person.get("from_date"),
                self.Membership.to_date: person.get("to_date")
            }).on_conflict(
                conflict_target=(self.Membership.person_id, self.Membership.organization_id),
                action="update",
                update={
                    self.Membership.from_date: person.get("from_date"),
                    self.Membership.to_date: person.get("to_date")
                }
            ).execute()
            self.db.commit()




