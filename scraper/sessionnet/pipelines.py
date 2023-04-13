
import scrapy.pipelines.files
from itemadapter import ItemAdapter

from peewee import *
from sessionnet.items import OrganizationItem
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
        self.Person = Table("persons", ("id", "person_id", "name")).bind(db)
        self.Organization = Table("organizations", ("id", "organization_id", "name")).bind(db)
        self.Membership = Table("memberships", ("id", "person_id", "organization_id", "from_date", "to_date")).bind(db)

    def close_spider(self, spider):
        spider.logger.info("Closing database connection")

    def process_item(self, item, spider):
        if isinstance(item, OrganizationItem):
            self.process_organization(item, spider)
        return item

    def process_organization(self, item, spider):
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




