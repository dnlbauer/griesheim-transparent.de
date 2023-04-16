import datetime

import pytz
from scrapy.item import Item, Field

class SessionNetItem(Item):
    last_updated = Field()
    id = Field()

    def __init__(self, *args, **kwargs):
        if "last_updated" not in kwargs.keys():
            kwargs["last_updated"] = datetime.datetime.now().astimezone(pytz.utc)
        super(SessionNetItem, self).__init__(*args, **kwargs)


class MeetingItem(SessionNetItem):
    title = Field()
    title_short = Field()
    date = Field()
    organization = Field()
    file_ids = Field()
    agenda_ids = Field()
    consultation_ids = Field()


class AgendaItem(SessionNetItem):
    title = Field()
    decision = Field()
    vote = Field()
    text = Field()
    file_ids = Field()
    consultation_ids = Field()


class ConsultationItem(SessionNetItem):
    name = Field()
    topic = Field()
    type = Field()
    text = Field()
    agenda_ids = Field()
    file_ids = Field()


class DocumentItem(SessionNetItem):
    file_name = Field()
    content_type = Field()
    file_urls = Field()
    files = Field()
    title = Field()


class OrganizationItem(SessionNetItem):
    title = Field()
    persons = Field()
