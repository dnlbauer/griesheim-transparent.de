import re
from datetime import datetime

import scrapy

from sessionnet.items import MeetingItem, DocumentItem, AgendaItem, ConsultationItem
from sessionnet.spiders.utils import add_url_parameters, get_url_params, clean_text
from sessionnet.url_suffices import meeting_url_to_suffix, meeting_document_link_suffix, agenda_url_link_suffix, \
    consultation_url_link_suffix, meeting_url_top_suffix, meeting_url_attendence_suffix
from sessionnet.urls import get_meeting_url


class SessionNetSpider(scrapy.Spider):
    name = "sessionnet"

    def start_requests(self):
        base_url = "https://sessionnet.krz.de/griesheim/bi/si0040.asp"
        years = [2022]
        months = range(2, 3)
        # months = range(2, 12)
        for year in years:
            params = { '__cjahr': year }
            for month in months:
                params["__cmonat"] = month
                url = add_url_parameters(base_url, params)
                yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response, **kwargs):
        return self.parse_calendar(response)

    def parse_calendar(self, response):
        yield from self.scrape_dom_for_meetings(response)

    def get_links(self, response, *links):
        found_links = []
        for link in links:
            found_links += response.selector.xpath(f"//a[contains(@href, '{link}')]//@href").getall()
        return list(set(found_links))

    def get_file_links(self, response):
        file_links = self.get_links(response, meeting_document_link_suffix)
        follows = [response.follow(file_link, callback=self.parse_file, method="HEAD") for file_link in file_links]
        ids = [get_url_params(file_link)["id"] for file_link in file_links]
        return ids, follows

    def scrape_dom_for_meetings(self, response):
        meeting_links = self.get_links(response, meeting_url_to_suffix, meeting_url_to_suffix, meeting_url_top_suffix, meeting_url_attendence_suffix)

        for link in meeting_links:
            meeting_id = get_url_params(link)["__ksinr"]
            yield response.follow(get_meeting_url(meeting_id), callback=self.parse_meeting)

    def parse_meeting(self, response):
        id = get_url_params(response.url)["__ksinr"]
        self.logger.info(f"Parsing meeting with id: {id}")

        title = response.selector.xpath("//h1//text()").get()
        if "Fehlermeldung" in title:
          error = " ".join(response.selector.xpath("//div[contains(@aria-label, 'Informationen')]")[0].getall())
          self.logger.error(f"Error crawling meeting {id}! Message: {error.strip()}")
          return

        info_table_selector_base = "//div[contains(@class, '{0}') and contains(@class, 'smc-dg-td-2')]//text()"
        title_short = response.selector.xpath(info_table_selector_base.format("siname")).get()
        organization = response.selector.xpath(info_table_selector_base.format("sigrname")).get()

        date = response.selector.xpath(info_table_selector_base.format("sidat")).get()
        date = datetime.strptime(date, "%d.%m.%Y")
        time = response.selector.xpath(info_table_selector_base.format("yytime")).get()
        # 18:00-18:50 Uhr -> 18:00 18:50 Uhr
        time = re.sub("\\-", " ", time)
        # 18:00 Uhr -> 18:00
        time = re.split('\\s+', time)[0]
        time = datetime.strptime(time, "%H:%M")

        file_ids, file_follows = self.get_file_links(response)
        for follow in file_follows:
            yield follow

        agenda_links = self.get_links(response, agenda_url_link_suffix)
        agenda_ids = []
        for agenda_link in agenda_links:
            agenda_id = get_url_params(agenda_link)["__ktonr"]
            agenda_ids.append(agenda_id)
            yield response.follow(agenda_link, callback=self.parse_agenda)

        consultation_links = self.get_links(response, consultation_url_link_suffix)
        consultation_ids = []
        for consultation_link in consultation_links:
            consultation_id = get_url_params(consultation_link)["__kvonr"]
            consultation_ids.append(consultation_id)
            yield response.follow(consultation_link, callback=self.parse_consultation)

        yield MeetingItem(
            id=id,
            title=title,
            title_short=title_short,
            organization=organization,
            date=datetime.combine(date.date(), time.time()),
            file_ids=file_ids,
            agenda_ids=agenda_ids,
            consultation_ids=consultation_ids
        )

    def parse_agenda(self, response, **kwargs):
        yield from self.scrape_dom_for_meetings(response)

        id = get_url_params(response.url)["__ktonr"]

        title = response.selector.xpath("//h1//text()").get()
        decision = response.selector.xpath("//p[contains(@class, 'smc_field_btname')]//text()").get()
        vote = response.selector.xpath("//p[contains(@class, 'smc_field_toabst')]//text()").get()

        text = response.selector.xpath("//div[contains(@class, 'WordSection1')]//p//text()").getall()
        text = clean_text(text)

        file_ids, file_follows = self.get_file_links(response)
        for follow in file_follows:
            yield follow

        consultation_links = self.get_links(response, consultation_url_link_suffix)
        consultation_ids = []
        for consultation_link in consultation_links:
            consultation_id = get_url_params(consultation_link)["__kvonr"]
            consultation_ids.append(consultation_id)
            yield response.follow(consultation_link, callback=self.parse_consultation)

        yield AgendaItem(
            id=id,
            title=title,
            decision=decision,
            vote=vote,
            text=text,
            file_ids=file_ids,
            consultation_ids=consultation_ids
        )


    def parse_consultation(self, response, **kwargs):
        id = get_url_params(response.url)["__kvonr"]

        topic = response.selector.xpath("//h1//text()").get()

        info_table_selector_base = "//div[contains(@class, '{0}') and contains(@class, 'smc-dg-td-2')]//text()"
        name = response.selector.xpath(info_table_selector_base.format("voname")).get()
        consultation_type = response.selector.xpath(info_table_selector_base.format("vovaname")).get()

        text = response.selector.xpath("//div[contains(@class, 'WordSection1')]//p//text()").getall()
        text = clean_text(text)

        file_ids, file_follows = self.get_file_links(response)
        for follow in file_follows:
            yield follow

        # TODO find additional meeting links from vo0053 (beratungen page for consultation)

        yield ConsultationItem(
            id=id,
            topic=topic,
            name=name,
            type=consultation_type,
            text=text,
            file_ids=file_ids
        )

    def parse_file(self, response, **kwargs):
        id = get_url_params(response.url)["id"]
        content_type = response.headers["Content-Type"].decode("utf-8").split(";")[0]
        file_name = response.headers["Content-Disposition"].decode("utf-8").split('"')[1]

        yield DocumentItem(
            id=id,
            file_name=file_name,
            content_type=content_type,
            file_urls=[response.url]
        )
