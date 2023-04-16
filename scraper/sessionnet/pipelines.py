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

        self.Person = Table("persons", ("id", "person_id", "name", "created_at", "last_modified")).bind(db)
        self.Organization = Table("organizations", ("id", "organization_id", "name", "created_at", "last_modified")).bind(db)
        self.Membership = Table("memberships", ("id", "person_id", "organization_id", "from_date", "to_date", "created_at", "last_modified")).bind(db)
        self.Meeting = Table("meetings", ("id", "meeting_id", "title", "title_short", "date", "organization_id", "created_at", "last_modified")).bind(db)
        self.Meeting_Document = Table("meetings_documents", ("id", "meeting_id", "document_id")).bind(db)
        self.Meeting_Consultation = Table("meetings_consultations", ("id", "meeting_id", "consultation_id")).bind(db)
        self.Consultation = Table("consultations", ("id", "consultation_id", "name", "topic", "type", "text", "created_at", "last_modified")).bind(db)
        self.Consultation_Document = Table("consultations_documents", ("id", "consultation_id", "document_id")).bind(db)
        self.AgendaItem = Table("agendaitems", ("id", "agenda_item_id", "title", "decision", "vote", "text", "consultation_id", "meeting_id", "created_at", "last_modified")).bind(db)
        self.AgendaItem_Document = Table("agendaitems_documents", ("id", "agendaitem_id", "document_id")).bind(db)
        self.Document = Table("documents", ("id", "document_id", "file_name", "uri", "content_type", "size", "title", "checksum", "created_at", "last_modified")).bind(db)

        self.meetings_organizations = []
        self.meetings_documents = []
        self.meetings_consultations = []
        self.meetings_agenda_items = []
        self.consultations_documents = []
        self.consultations_agenda_items = []
        self.agenda_items_documents = []
        self.agenda_items_consultations = []


    def close_spider(self, spider):
        spider.logger.info("Updating meeting organizations")
        for (meeting_id, organization_name) in self.meetings_organizations:
            organization_fk = self.Organization.select(self.Organization.id).where(self.Organization.name == organization_name).first()['id']
            self.Meeting.update(organization_id=organization_fk).where(self.Meeting.meeting_id == int(meeting_id)).execute()

        spider.logger.info("Updating meeting relations")
        self.db.begin()
        for (meeting_id, document_ids) in self.meetings_documents:
            meeting_fk = self.Meeting.select(self.Meeting.id).where(self.Meeting.meeting_id == meeting_id).first()['id']
            for document_id in document_ids:
                document_fk = self.Document.select(self.Document.id).where(self.Document.document_id == document_id).first()['id']
                if not self.Meeting_Document.select("id").where((self.Meeting_Document.meeting_id == meeting_fk) & (self.Meeting_Document.document_id == document_fk)).exists():
                    self.Meeting_Document.insert({
                        self.Meeting_Document.meeting_id: meeting_fk,
                        self.Meeting_Document.document_id: document_fk
                    }).execute()
        for (meeting_id, consultation_ids) in self.meetings_consultations:
            meeting_fk = self.Meeting.select(self.Meeting.id).where(self.Meeting.meeting_id == meeting_id).first()['id']
            for consultation_id in consultation_ids:
                consultation_fk = self.Consultation.select(self.Consultation.id).where(self.Consultation.consultation_id == consultation_id).first()['id']
                if not self.Meeting_Consultation.select("id").where((self.Meeting_Consultation.meeting_id == meeting_fk) & (self.Meeting_Consultation.consultation_id == consultation_fk)).exists():
                    self.Meeting_Consultation.insert({
                        self.Meeting_Consultation.meeting_id: meeting_fk,
                        self.Meeting_Consultation.consultation_id: consultation_fk
                    }).execute()

        spider.logger.info("Updating consultation relations")
        for (consultation_id, document_ids) in self.consultations_documents:
            consultation_fk = self.Consultation.select(self.Consultation.id).where(self.Consultation.consultation_id == consultation_id).first()['id']
            for document_id in document_ids:
                document_fk = self.Document.select(self.Document.id).where(self.Document.document_id == document_id).first()['id']
                if not self.Consultation_Document.select("id").where((self.Consultation_Document.consultation_id == consultation_fk) & (self.Consultation_Document.document_id == document_fk)).exists():
                    self.Consultation_Document.insert({
                        self.Consultation_Document.consultation_id: consultation_fk,
                        self.Consultation_Document.document_id: document_fk
                    }).execute()

        spider.logger.info("Updating agenda item relations")
        for (meeting_id, agenda_ids) in self.meetings_agenda_items:
            meeting_fk = self.Meeting.select(self.Meeting.id).where(self.Meeting.meeting_id == meeting_id).first()['id']
            self.AgendaItem.update(meeting_id=meeting_fk).where(self.AgendaItem.agenda_item_id << agenda_ids).execute()

        for (agenda_item_id, document_ids) in self.agenda_items_documents:
            agenda_item_fk = self.AgendaItem.select(self.AgendaItem.id).where(self.AgendaItem.agenda_item_id == agenda_item_id).first()['id']
            for document_id in document_ids:
                document_fk = self.Document.select(self.Document.id).where(self.Document.document_id == document_id).first()['id']
                if not self.AgendaItem_Document.select("id").where((self.AgendaItem_Document.agendaitem_id == agenda_item_fk) & (self.AgendaItem_Document.document_id == document_fk)).exists():
                    self.AgendaItem_Document.insert({
                        self.AgendaItem_Document.agendaitem_id: agenda_item_fk,
                        self.AgendaItem_Document.document_id: document_fk
                    }).execute()
        for (agenda_item_id, consultation_ids) in self.agenda_items_consultations:
            assert len(consultation_ids) <= 1
            if len(consultation_ids) == 1:
                self.AgendaItem.update(consultation_id=consultation_ids[0]).where(self.AgendaItem.agenda_item_id == agenda_item_id).execute()

        self.db.commit()

        spider.logger.info("Closing database connection")
        self.db.close()

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
            self.Meeting.created_at: item.get("last_updated"),
            self.Meeting.last_modified: item.get("last_updated")
        }).on_conflict(
            conflict_target=self.Meeting.meeting_id,
            action="update",
            update={
                self.Meeting.title: item.get("title"),
                self.Meeting.title_short: item.get("title_short"),
                self.Meeting.date: item.get("date"),
                self.Meeting.last_modified: item.get("last_updated")
            }
        ).execute()
        self.meetings_organizations.append((item.get('id'), item.get("organization")))
        self.meetings_documents.append((item.get("id"), item.get("file_ids")))
        self.meetings_consultations.append((item.get("id"), item.get("consultation_ids")))
        self.meetings_agenda_items.append((item.get("id"), item.get("agenda_ids")))

    def process_consultations(self, item, spider):
        self.Consultation.insert({
            self.Consultation.consultation_id: item.get("id"),
            self.Consultation.name: item.get("name"),
            self.Consultation.topic: item.get("topic"),
            self.Consultation.type: item.get("type"),
            self.Consultation.text: item.get("text"),
            self.Consultation.created_at: item.get("last_updated"),
            self.Consultation.last_modified: item.get("last_updated")
        }).on_conflict(
            conflict_target=self.Consultation.consultation_id,
            action="update",
            update={
                self.Consultation.name: item.get("name"),
                self.Consultation.topic: item.get("topic"),
                self.Consultation.type: item.get("type"),
                self.Consultation.text: item.get("text"),
                self.Consultation.last_modified: item.get("last_updated")
            }
        ).execute()
        self.consultations_documents.append((item.get("id"), item.get("file_ids")))
        self.consultations_agenda_items.append((item.get("id"), item.get("agenda_ids")))

    def process_agenda_item(self, item, spider):
        self.AgendaItem.insert({
            self.AgendaItem.agenda_item_id: item.get("id"),
            self.AgendaItem.title: item.get("title"),
            self.AgendaItem.decision: item.get("decision"),
            self.AgendaItem.vote: item.get("vote"),
            self.AgendaItem.text: item.get("text"),
            self.AgendaItem.created_at: item.get("last_updated"),
            self.AgendaItem.last_modified: item.get("last_updated")
        }).on_conflict(
            conflict_target=self.AgendaItem.agenda_item_id,
            action="update",
            update={
                self.AgendaItem.title: item.get("title"),
                self.AgendaItem.decision: item.get("decision"),
                self.AgendaItem.vote: item.get("vote"),
                self.AgendaItem.text: item.get("text"),
                self.AgendaItem.last_modified: item.get("last_updated")
            }
        ).execute()
        self.agenda_items_documents.append((item.get("id"), item.get("file_ids")))
        self.agenda_items_consultations.append((item.get("id"), item.get("consultation_ids")))

    def process_document(self, item, spider):
        path = os.path.join(spider.settings.get("FILES_STORE"), item.get("files")[0].get("path"))
        size = os.path.getsize(path)

        self.Document.insert({
            self.Document.document_id: item.get("id"),
            self.Document.file_name: item.get("file_name"),
            self.Document.content_type: item.get("content_type"),
            self.Document.checksum: item.get("files")[0]["checksum"],
            self.Document.uri: item.get("files")[0]["path"],
            self.Document.size: size,
            self.Document.title: item.get("title"),
            self.Document.created_at: item.get("last_updated"),
            self.Document.last_modified: item.get("last_updated")
        }).on_conflict(
            conflict_target=self.Document.document_id,
            action="update",
            update={
                self.Document.file_name: item.get("file_name"),
                self.Document.content_type: item.get("content_type"),
                self.Document.checksum: item.get("files")[0]["checksum"],
                self.Document.uri: item.get("files")[0]["path"],
                self.Document.size: size,
                self.Document.title: item.get("title"),
                self.Document.last_modified: item.get("last_updated")
            }
        ).execute()

    def process_organization(self, item, spider):
        self.db.begin()
        self.Organization.insert({
            self.Organization.organization_id: item.get("id"),
            self.Organization.name: item.get("title"),
            self.Organization.created_at: item.get("last_updated"),
            self.Organization.last_modified: item.get("last_updated")
        }).on_conflict(
            conflict_target=self.Organization.organization_id,
            action="update",
            update={
                self.Organization.name: item.get("title"),
                self.Organization.last_modified: item.get("last_updated")
            }
        ).execute()
        organization_id = self.Organization.select(self.Organization.id).where(self.Organization.organization_id == item.get('id')).first().get('id')

        for person in item.get("persons"):
            self.Person.insert({
                self.Person.person_id: person.get("id"),
                self.Person.name: person.get("name"),
                self.Person.created_at: item.get("last_updated"),
                self.Person.last_modified: item.get("last_updated")
            }).on_conflict(
                conflict_target=self.Person.name,
                action="update",
                update={
                    self.Person.name: person.get("name"),
                    self.Person.last_modified: item.get("last_updated")
                }
            ).execute()
            person_id = self.Person.select(self.Person.id).where(self.Person.name == person.get("name")).first().get("id")
            self.Membership.insert({
                self.Membership.person_id: person_id,
                self.Membership.organization_id: organization_id,
                self.Membership.from_date: person.get("from_date"),
                self.Membership.to_date: person.get("to_date"),
                self.Membership.created_at: item.get("last_updated"),
                self.Membership.last_modified: item.get("last_updated")
            }).on_conflict(
                conflict_target=(self.Membership.person_id, self.Membership.organization_id),
                action="update",
                update={
                    self.Membership.from_date: person.get("from_date"),
                    self.Membership.to_date: person.get("to_date"),
                    self.Membership.last_modified: item.get("last_updated")
                }
            ).execute()
        self.db.commit()




