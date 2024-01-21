import re
from datetime import datetime
from collections import namedtuple

import pytz as pytz
import scrapy

from sessionnet.items import MeetingItem, DocumentItem, AgendaItem, ConsultationItem, OrganizationItem
from sessionnet.utils import add_url_parameters, get_url_params, clean_text, remove_url_parameters
from sessionnet.url_suffices import meeting_url_to_suffix, meeting_document_link_suffix, agenda_url_link_suffix, \
    consultation_url_link_suffix, meeting_url_top_suffix, meeting_url_attendence_suffix, \
    organizations_details_url_suffix
from sessionnet.urls import get_meeting_url

Link = namedtuple("Link", "link text")

class SessionNetSpider(scrapy.Spider):
    name = "sessionnet"

    organizations_base_url = "https://sessionnet.krz.de/griesheim/bi/gr0040.asp?__cwpall=1&"
    persons_base_url = "https://sessionnet.krz.de/griesheim/bi/kp0041.asp?__cwpall=1&"
    calendar_base_url = "https://sessionnet.krz.de/griesheim/bi/si0040.asp"

    def start_requests(self):
        if self.settings.get("SCRAPE_ORGANIZATIONS"):
            self.logger.info("Seeding organizations")
            yield scrapy.Request(url=self.organizations_base_url, callback=self.parse)
            self.logger.info("Seeding Persons")
            yield scrapy.Request(url=self.persons_base_url, callback=self.parse)

        if self.settings.get("SCRAPE_MEETINGS"):
            start_month, start_year = self.settings.get("SCRAPE_START").split("/")
            end_month, end_year = self.settings.get("SCRAPE_END").split("/")
            self.logger.info(f"Seeding calendar months from {start_month}/{start_year} to {end_month}/{end_year}")
            years = range(int(start_year), int(end_year)+1)
            months = range(1, 13)
            for year in years:
                params = {'__cjahr': year}
                for month in months:
                    if year == int(start_year) and month < int(start_month):
                        continue
                    if year == int(end_year) and month > int(end_month):
                        continue
                    params["__cmonat"] = month
                    url = add_url_parameters(self.calendar_base_url, params)
                    yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response, **kwargs):
        if response.url.startswith(self.calendar_base_url):
            yield from self.parse_calendar(response)
        if response.url.startswith(self.organizations_base_url):
            yield from self.parse_organizations_overview(response)
        if response.url.startswith(self.persons_base_url):
            yield from self.parse_persons_overview(response)

    def parse_persons_overview(self, response):
        self.logger.info("Parse person overview")
        rows = response.selector.xpath("//table[contains(@class, 'table-striped')]//tbody//tr")
        organizations = {}
        for row in rows:
            name = row.xpath("td[contains(@data-label, 'Name')]//text()").get()
            organization = row.xpath("td[contains(@data-label, 'Mitgliedschaft')]//text()").get()
            to_date = row.xpath("td[contains(@data-label, 'Ende')]//text()").get()
            if to_date:
                to_date = datetime.strptime(to_date, "%d.%m.%Y")
            person = dict(
                name=name,
                to_date=to_date
            )
            if organization in organizations:
                organizations[organization].append(person)
            else:
                organizations[organization] = [person]

        for organization in organizations:
            yield OrganizationItem(
                title=organization,
                persons=organizations[organization]
            )

    def parse_organizations_overview(self, response):
        self.logger.info("Parse organization overview")
        scrapeable_organizations = response.selector.xpath(f"//a[contains(@href, '{organizations_details_url_suffix}')]//@href").getall()
        scrapeable_organizations_names = response.selector.xpath(f"//a[contains(@href, '{organizations_details_url_suffix}')]//text()").getall()
        organizations_names = response.selector.xpath(f"//td[contains(@class, 'grname')]//text()").getall()
        for link in scrapeable_organizations:
            # get all
            link = add_url_parameters(link, {"__cwpall": 1})
            link = remove_url_parameters(link, ["cwpnr"])
            yield response.follow(url=link, callback=self.parse_organization)
        for name in organizations_names:
            if name in scrapeable_organizations_names:
                continue
            yield OrganizationItem(
                title=name,
                persons=[]
            )

    def parse_organization(self, response, **kwargs):
        id = get_url_params(response.url)["__kgrnr"]
        title = response.selector.xpath("//h1//text()").get()
        self.logger.info(f"Parse organization: {title} ({id})")

        persons = []
        persons_table = response.selector.xpath("//table[contains(@class, 'table')]//tbody//tr")
        selector_organizations_mandate_base = "td[@data-label='{0}']//text()"
        for person in persons_table:
            person_id = person.xpath("td[@data-label='Name']//a//@href").get()
            if person_id:
                person_id = get_url_params(person_id)["__kpenr"]
            name = person.xpath(selector_organizations_mandate_base.format("Name")).get()
            if not name:
                continue
            type = person.xpath(selector_organizations_mandate_base.format("Mitarbeit")).get()
            from_date = person.xpath(selector_organizations_mandate_base.format("Beginn")).get()
            if from_date:
                from_date = datetime.strptime(from_date, "%d.%m.%Y")
            to_date = person.xpath(selector_organizations_mandate_base.format("Ende")).get()
            if to_date:
                to_date = datetime.strptime(to_date, "%d.%m.%Y")
            persons.append(dict(
                id=person_id,
                name=name,
                type=type,
                from_date=from_date,
                to_date=to_date
            ))


        yield OrganizationItem(
            id=id,
            title=title,
            persons=persons
        )


    def parse_calendar(self, response):
        params = get_url_params(response.url)
        self.logger.info(f"Seeding from calendar {params['__cmonat']}/{params['__cjahr']}")
        yield from self.scrape_dom_for_meetings(response)

    def get_links(self, response, *links):
        found_links = []
        for link in links:
            found_links += response.selector.xpath(f"//a[contains(@href, '{link}')]")
        found_links = [Link(link.xpath("@href").get(), link.xpath("text()").get()) for link in found_links]
        found_links = [link for link in found_links if link.text is not None]
        return list(set(found_links))

    def get_file_links(self, response):
        file_links = self.get_links(response, meeting_document_link_suffix)
        follows = [response.follow(file_link.link, callback=self.parse_file, method="HEAD", meta={"title": file_link.text}) for file_link in file_links]
        ids = [get_url_params(file_link.link)["id"] for file_link in file_links]
        return ids, follows

    def scrape_dom_for_meetings(self, response):
        meeting_links = [link.link for link in self.get_links(response, meeting_url_to_suffix, meeting_url_to_suffix, meeting_url_top_suffix, meeting_url_attendence_suffix)]

        for link in meeting_links:
            meeting_id = get_url_params(link)["__ksinr"]
            yield response.follow(get_meeting_url(meeting_id), callback=self.parse_meeting)

    def parse_meeting(self, response):
        id = get_url_params(response.url)["__ksinr"]

        title = response.selector.xpath("//h1//text()").get()
        self.logger.info(f"Parsing meeting: {title} ({id})")
        if "Fehlermeldung" in title:
          error = " ".join(response.selector.xpath("//div[contains(@aria-label, 'Informationen')]")[0].getall())
          self.logger.error(f"Error crawling meeting {id}! Message: {error.strip()}")
          return

        info_table_selector_base = "//div[not(contains(@class, 'smc-cell-head')) and contains(@class, 'smc-table-cell') and contains(@class, '{0}')]//text()"
        title_short = response.selector.xpath(info_table_selector_base.format("siname")).get()
        organization = response.selector.xpath(info_table_selector_base.format("sigrname")).get()

        date = response.selector.xpath(info_table_selector_base.format("sidat")).get()
        if date:
            date = datetime.strptime(date, "%d.%m.%Y").replace(tzinfo=pytz.timezone("Europe/Berlin"))
        time = response.selector.xpath(info_table_selector_base.format("yytime")).get()
        if time:
            # 18:00-18:50 Uhr -> 18:00 18:50 Uhr
            time = re.sub("\\-", " ", time)
            # 18:00 Uhr -> 18:00
            time = re.split('\\s+', time)[0]
            time = datetime.strptime(time, "%H:%M").replace(tzinfo=pytz.timezone("Europe/Berlin"))

        if date and time:
            date = datetime.combine(date.date(), time.time()).astimezone(pytz.utc)


        file_ids, file_follows = self.get_file_links(response)
        for follow in file_follows:
            yield follow

        agenda_links = [link.link for link in self.get_links(response, agenda_url_link_suffix)]
        agenda_ids = []
        for agenda_link in agenda_links:
            agenda_id = get_url_params(agenda_link)["__ktonr"]
            agenda_ids.append(agenda_id)
            yield response.follow(agenda_link, callback=self.parse_agenda)

        consultation_links = [link.link for link in self.get_links(response, consultation_url_link_suffix)]
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
            date=date,
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

        consultation_links = [link.link for link in self.get_links(response, consultation_url_link_suffix)]
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

        info_table_selector_base = "//div[not(contains(@class, 'smc-cell-head')) and contains(@class, '{0}') and contains(@class, 'smc-table-cell')]//text()"
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

        if "title" in response.meta:
            title = response.meta["title"]
        else:
            title = None

        yield DocumentItem(
            id=id,
            file_name=file_name,
            content_type=content_type,
            file_urls=[response.url],
            title=title
        )
