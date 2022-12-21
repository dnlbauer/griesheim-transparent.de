import multiprocessing
import re
import threading
import time
import logging
import urllib
from datetime import datetime
from multiprocessing import Process
from multiprocessing.managers import BaseManager
from queue import LifoQueue
from threading import Lock
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse, parse_qs

import mechanize as mechanize
import structlog
from lxml import html
from nameparser import HumanName
from structlog import get_logger

from db import Repository
from db.Schema import Schema
from db.models import *
from utils import chunks, clean_string, parse_args, parse_config_and_args

logger = get_logger()


def init_queue_meetings_calendar(start_month, start_year, end_month, end_year, queue):
    logger.info("Scraping meeting calendar...")

    years = list(range(start_year, end_year + 1))
    months = list(range(1, 13))
    items = []
    for year in years:
        for month in months:
            if year == start_year and month < start_month:
                continue
            if year == end_year and month > end_month:
                continue
            items.append((month, year))

    logger.info(f"Inserting {len(items)} calendar items into queue")
    for item in items:
        queue.put(QueueItem("calendar", item))


def scrape_calendar_month(month, year, config, queue):
    logger.info(f"Scraping meeting calendar: {month}/{year}")
    url = f'{config["base_url"]}{config["calendar_url_suffix"]}?{urlencode({"__cjahr": str(year), "__cmonat": str(month)})}'
    logger.debug(url)
    dom = get_dom(url)

    links = dom.xpath(config["xml_selectors"]["meeting_link"])
    links = [link for link in links if config["meeting_url_link_suffix"] in link]

    meeting_ids = []
    for rel_link in links:
        match = re.search("ksinr=(\d*)", rel_link)
        if match and match.group(1) not in meeting_ids:
            meeting_ids.append(match.group(1))
    logger.info(f"{month}/{year}: {len(meeting_ids)} meetings")

    for meeting_id in meeting_ids:
        queue.put(QueueItem("meeting", meeting_id))


def init_queue_with_drafts(config, queue):
    logger.info(f"Scraping consultation drafts")
    url = f'{config["base_url"]}{config["consultation_new_link_suffix"]}?__caktuell=2'
    logger.debug(url)
    dom = get_dom(url)

    links = dom.xpath("//a/@href")
    links = list(set([l for l in links if config["consultation_url_link_suffix"] in l]))
    for link in links:
        parsed_link = urlparse(link)
        query_params = parse_qs(parsed_link.query)
        link_id = query_params["__kvonr"][0]
        queue.put(QueueItem("consultation", link_id))


def init_queue_meetings_systematic(start_id, stop_id, queue):
    for meeting_id in range(start_id, stop_id + 1):
        queue.put(QueueItem("meeting", meeting_id))


def init_queue_documents_systematic(start_id, stop_id, queue):
    for document_id in range(start_id, stop_id + 1):
        queue.put(QueueItem("document", document_id))


def scrape_meeting(id, config, db, queue, lock):
    logger.info(f"Scraping meeting with id: {id}")
    url = f'{config["base_url"]}{config["meeting_url_overview_suffix"]}?{urlencode({"__ksinr": str(id)})}'
    logger.debug(url)
    dom = get_dom(url)

    # parse title
    title = clean_string(dom.xpath("//h1")[0].text)

    if "Fehlermeldung" in title:
        error = " ".join(dom.xpath("//div[contains(@aria-label, 'Informationen')]")[0].itertext())
        logger.info(f"Error! Message: {error.strip()}")
        return
    logger.info(f"Title: {title}")

    # parse general information
    cells = dom.xpath(config["xml_selectors"]["meeting_information_table"])
    pairs = chunks(cells, 2)
    meeting_date = None
    title_short = None
    organization = None
    for (name_elem, value_elem) in pairs:
        name = name_elem.text
        value = value_elem.text
        if name == "Gremium":
            organization = value
        if name == "Datum":
            meeting_date = datetime.strptime(value, "%d.%m.%Y")
        if name == "Sitzung":
            title_short = value

    # find general page attachments
    document_ids = scrape_dom_for_documents(dom, config, db, queue, lock)

    # scrape agenda list
    logger.debug(f"Scraping meeting agenda list")
    url = f'{config["base_url"]}{config["meeting_url_agenda_suffix"]}?{urlencode({"__ksinr": str(id)})}'
    logger.debug(url)
    dom = get_dom(url)
    links = dom.xpath(config["xml_selectors"]["meeting_agenda_link"])
    agenda_item_ids = []
    for link in links:
        parsed_link = urlparse(link)
        query_params = parse_qs(parsed_link.query)
        link_id = query_params["__ktonr"][0]
        scrape_agenda_item(link_id, config, db, queue, lock)
        agenda_item_ids.append(link_id)
    agenda_item_ids = [agenda_item_id for agenda_item_id in agenda_item_ids if agenda_item_id is not None]

    # scrape conultation list: required because agenda items are not available sometimes (i.e. future meetings)
    consultation_ids = scrape_dom_for_consultations(dom, config, db, queue, lock)

    # insert into db
    lock.acquire()
    with db.create_transaction() as t:
        repository = Repository(t.session)
        documents = [repository.find_document_by_id(i) for i in document_ids]
        agenda_items = [repository.find_agenda_item_by_agenda_item_id(i) for i in agenda_item_ids]
        consultations = [repository.find_consultation_by_consultation_id(i) for i in consultation_ids]
        organization_id = None
        organization = repository.find_organization_by_name(organization)
        if organization != None:
            organization_id = organization.id

        if repository.has_meeting_by_id(id):
            meeting = repository.find_meeting_by_id(id)
        else:
            meeting = Meeting()

        meeting.meeting_id = id
        meeting.title = title
        meeting.title_short = title_short
        meeting.date = meeting_date
        for document in documents:
            if document not in meeting.documents:
                meeting.documents.append(document)
        meeting.agendaItems = agenda_items
        meeting.consultations = consultations
        meeting.organization_id = organization_id
        repository.add_meeting(meeting)
        repository.commit()
        if (not repository.has_meeting_by_id(id)):
            logger.info(f"New meeting inserted")
        else:
            logger.debug(f"Meeting upserted")
    lock.release()


def scrape_agenda_item(id, config, db, queue, lock):
    logger.info(f"Scraping agenda item {id}")
    url = f'{config["base_url"]}{config["agenda_url_link_suffix"]}?{urlencode({"__ktonr": id})}'
    logger.debug(url)
    dom = get_dom(url)

    title = dom.xpath("//h1")[0]
    title = clean_string(title.text)
    logger.debug(title)

    decision = dom.xpath(config["xml_selectors"]["agenda_item_decision"])
    if len(decision) == 0:
        decision = None
    else:
        decision = clean_string("".join(decision[0].itertext()).split(":", 1)[-1])

    vote = dom.xpath(config["xml_selectors"]["agenda_item_vote"])
    if len(vote) == 0:
        vote = None
    else:
        vote = clean_string("".join(vote[0].itertext()).split(":", 1)[-1])

    consultation_ids = scrape_dom_for_consultations(dom, config, db, queue, lock)
    assert(len(consultation_ids) <= 1)
    if len(consultation_ids) == 0:
        consultation_id = None
    else:
        consultation_id = consultation_ids[0]

    text = dom.xpath(config["xml_selectors"]["agenda_item_text"])
    if len(text) == 0:
        text = None
    elif len(text) > 0:
        parsed_text = ""
        for t in text:
            parsed_text += "".join(t.itertext())
        parsed_text = clean_string(parsed_text)
        while "  " in parsed_text:
            parsed_text = text.replace("  ", " ")
        text = parsed_text

    document_ids = scrape_dom_for_documents(dom, config, db, queue, lock)

    lock.acquire()
    with db.create_transaction() as t:
        repository = Repository(t.session)
        documents = [repository.find_document_by_id(doc_id) for doc_id in document_ids]
        if consultation_id != None:
            consultation_id = repository.find_consultation_by_consultation_id(consultation_id).id
        if repository.has_agenda_item_by_agenda_item_id(id):
            item = repository.find_agenda_item_by_agenda_item_id(id)
        else:
            item = AgendaItem()
        item.agenda_item_id = id
        item.title = title
        item.text = text
        item.decision = decision
        item.vote = vote
        item.documents = documents
        item.consultation_id = consultation_id
        repository.add_agenda_item(item)
        repository.commit()
    lock.release()


def scrape_dom_for_consultations(dom, config, db, queue, lock):
    consultation_ids = []
    links = dom.xpath("//a/@href")
    links = list(set([l for l in links if config["consultation_url_link_suffix"] in l]))
    for link in links:
        parsed_link = urlparse(link)
        query_params = parse_qs(parsed_link.query)
        link_id = query_params["__kvonr"][0]
        consultation_id = scrape_consultation(link_id, config, db, queue, lock)
        consultation_ids.append(link_id)
    return consultation_ids


def scrape_consultation(id, config, db, queue, lock):
    logger.info(f"Scraping consultation item {id}")
    url = f'{config["base_url"]}{config["consultation_url_link_suffix"]}?{urlencode({"__kvonr": id})}'
    logger.debug(url)
    dom = get_dom(url)

    topic = "".join(dom.xpath("//h1")[0].itertext())
    topic = clean_string(topic)

    name = dom.xpath(config["xml_selectors"]["consultation_name"])
    if len(name) < 2:
        name = None
    else:
        name = clean_string(name[1].text)

    consultation_type = dom.xpath(config["xml_selectors"]["consultation_type"])
    if len(consultation_type) < 2:
        consultation_type = None
    else:
        consultation_type = clean_string(consultation_type[1].text)

    text = dom.xpath(config["xml_selectors"]["consultation_text"])
    if len(text) == 0:
        text = None
    elif len(text) > 0:
        parsed_text = ""
        for t in text:
            parsed_text += "".join(t.itertext())
        parsed_text = clean_string(parsed_text)
        while "  " in parsed_text:
            parsed_text = text.replace("  ", " ")
        text = parsed_text

    document_ids = scrape_dom_for_documents(dom, config, db, queue, lock)

    lock.acquire()
    with db.create_transaction() as t:
        repository = Repository(t.session)
        documents = [repository.find_document_by_id(i) for i in document_ids]

        if repository.has_consultation_by_consultation_id(id):
            consultation = repository.find_consultation_by_consultation_id(id)
        else:
            consultation = Consultation()
        consultation.consultation_id = id
        consultation.topic = topic
        consultation.type = consultation_type
        consultation.name = name
        consultation.text = text
        consultation.documents = documents
        repository.add_consultation(consultation)
        repository.commit()
        uuid = consultation.id
    lock.release()
    return uuid


def scrape_dom_for_documents(dom, config, db, queue, lock):
    links_elements = dom.xpath(config["xml_selectors"]["document_link"])
    links = []
    # filter links: href attribute and link text is required
    for l in links_elements:
        link_text = l.text_content()
        if len(link_text) == 0 or len(l.xpath('./@href')) == 0:
            continue
        else:
            links.append((link_text, l.xpath('./@href')[0]))

    # only keep links pointing to a file
    links = [link for link in links if "getfile.asp" in link[1] and len(link[0]) > 0]
    links = set(links)
    logger.debug(f"Found {len(links)} attachments")
    document_ids = []
    for (link_text, link) in links:
        parsed_link = urlparse(link)
        query_params = parse_qs(parsed_link.query)
        link_id = query_params["id"][0]
        scrape_document(link_id, config, db, queue, lock, title=link_text)
        document_ids.append(link_id)

    return document_ids


def scrape_document(id, config, db, queue, lock, title=None):
    logger.info(f"Scraping document id {id}")
    exists = False
    lock.acquire()
    with db.create_transaction() as t:
        repository = Repository(t.session)
        if repository.has_document_by_id(id):
            logger.debug(f"Document with id {id} already in database. Download will be skipped")
            # even if doc exists, update metadata
            document = repository.find_document_by_id(id)
            document.title = title
            repository.add_document(document)
            repository.commit()
            exists = True
    lock.release()
    if exists:
        return
    try:
        document = download_document(id, config, title)
    except urllib.error.URLError as e:
        if e.code == 403 or e.code == 404:
            return
        else:
            raise e
    lock.acquire()
    with db.create_transaction() as t:
        repository = Repository(t.session)
        if document is not None:
            repository.add_document(document)
            repository.session.commit()

    logger.info(f"New document inserted: {document.file_name} ({id})")
    lock.release()


def download_document(id, config, title=None):
    url = f'{config["base_url"]}{config["meeting_document_link_suffix"]}?{urlencode({"id": id})}'
    logger.debug(url)
    response = urllib.request.urlopen(url)

    if response.code != 200:
        logger.error(f"Failed to donwload document (id={id})")
        return None

    file_name = response.info().get_filename()
    content_type = response.info().get_content_type()
    content = response.read()

    return Document(
        document_id=id,
        file_name=file_name,
        content_type=content_type,
        content_binary=content,
        size=len(content),
        title=title
    )

def get_dom(url):
    browser = mechanize.Browser()
    browser.set_handle_robots(False)
    browser.addheaders = [("User-agent", "RIScraper was here. :)")]
    response = browser.open(url)
    if response.code != 200:
        raise ConnectionError(f"Failed to scrape mandate page (http=${response.code}")
    else:
        return html.parse(response)


def scrape_persons(db, config, lock):
    logger.info("Scraping persons...")
    url = f'{config["base_url"]}{config["mandate_holder_url_suffix"]}?{urlencode({"__cwpall": "1"})}'
    logger.debug(url)
    dom = get_dom(url)
    fields = dom.xpath(config["xml_selectors"]["mandate_row"])

    persons_n_memberships = []
    for chunk in chunks(fields, 4):
        name = "".join(chunk[0].itertext())
        name = HumanName(name)
        membership_string = "".join(chunk[1].itertext())
        persons_n_memberships.append(
            [Person(first_name=name.first, last_name=name.last), membership_string]
        )
    logger.debug(f"Found {len(persons_n_memberships)} persons")

    # add all persons and their organizations
    lock.acquire()
    with db.create_transaction() as transaction:
        repository = Repository(transaction.session)
        for (person, membership_string) in persons_n_memberships:
            repository.add_person_with_membership(
                person,
                Organization(name=membership_string),
            )
        repository.commit()
    lock.release()


def scrape_organizations(config, queue):
    logger.info("Scraping organizations...")
    url = f'{config["base_url"]}{config["organizations_url_suffix"]}?{urlencode({"__cwpall": "1"})}'
    logger.debug(url)
    dom = get_dom(url)
    fields = dom.xpath(config["xml_selectors"]["organizations_row"])

    # find scrapeable organizations
    org_ids = []
    for field in fields:
        rel_links = field.xpath("//a/@href")
        for rel_link in rel_links:
            if config["organizations_details_url_suffix"] not in rel_link:
                continue
            match = re.search("kgrnr=(\d*)", rel_link)
            if match and match.group(1) not in org_ids:
                org_ids.append(match.group(1))
    logger.debug(f"Found {len(org_ids)} organizations")

    for id in org_ids:
        queue.put(QueueItem("organization", id))


def scrape_organization(org_id, config, db, lock):
    logger.info(f"Scraping organization with id: {org_id}")
    url = f'{config["base_url"]}{config["organizations_details_url_suffix"]}?{urlencode({"__kgrnr": str(org_id), "__cwpall": "1"})}'
    logger.debug(url)
    dom = get_dom(url)

    title = dom.xpath("//h1")[0].text.replace("\xc2\xa0", " ")
    organization = Organization(name=title, org_id=org_id)

    persons = []
    names = dom.xpath(config["xml_selectors"]["organizations_mandate_name"])
    for name in names:
        name = HumanName("".join(name.itertext()))
        person = Person(first_name=name.first, last_name=name.last)
        persons.append(person)
    logger.debug(f"Organization {title}: {len(persons)} persons")

    lock.acquire()
    with db.create_transaction() as t:
        r = Repository(t.session)
        for person in persons:
            r.add_person_with_membership(person, organization)
        r.commit()
    lock.release()


class QueueItem:
    def __init__(self, type, id):
        self.type = type
        self.id = id


def processor(queue, config, loglevel, timeout, lock):
    global logger
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(loglevel))
    logger = get_logger().bind(thread=threading.get_ident())
    db = Schema(config["database_url"], verbose=False)
    while True:
        try:
            item = queue.get(timeout=timeout)
        except:
            logger.warning("Queue empty. Finishing task")
            break
        logger = logger.bind(type=item.type, id=item.id)
        try:
            if item.type == "persons":
                scrape_persons(db, config, lock)
            elif item.type == "organizations":
                scrape_organizations(config, queue)
            elif item.type == "organization":
                scrape_organization(item.id, config, db, lock)
            elif item.type == "meeting":
                scrape_meeting(item.id, config, db, queue, lock)
            elif item.type == "document":
                scrape_document(item.id, config, db, queue, lock)
            elif item.type == "calendar":
                scrape_calendar_month(*item.id, config, queue)
            elif item.type == "consultation":
                scrape_consultation(item.id, config, db, queue, lock)
            else:
                raise ValueError(f"Unknown queue item type: {item.type}, {item.id}")
        except KeyboardInterrupt as e:
            queue.close()
            raise e
        except BaseException as e:
            logger.error(f"Exception during processing {item.type}, {item.id}: {e}")
            logger.exception(e)


class MyManager(BaseManager):
    pass


def scrape(config):
    start = time.time()

    MyManager.register("MyQueue", LifoQueue)
    MyManager.register("Lock", Lock)
    manager = MyManager()
    manager.start()
    queue = manager.MyQueue()
    lock = manager.Lock()
    num_threads = config["nscraper"]

    # scrape organizatios/persons first so meetings can be mapped to organizations
    if config["organizations"]:
        queue.put(QueueItem("organizations", None))
    if config["persons"]:
        queue.put(QueueItem("persons", None))
    if queue.qsize() > 0:
        logger.info(f"Scraping organizational data with {num_threads} threads ...")
        processes = [Process(target=processor, args=(queue, config, loglevel, 1, lock)) for _ in range(num_threads)]
        try:
            [process.start() for process in processes]
            [process.join() for process in processes]
        except KeyboardInterrupt:
            [process.terminate() for process in processes]

    # scrape meetings
    if config['meeting']:
        queue.put(QueueItem('meeting', config['meeting']))
    elif config["systematic"]:
        init_queue_meetings_systematic(1, 10000, queue)
        init_queue_documents_systematic(1, 5000, queue)
    else:
        init_queue_with_drafts(config, queue)
        init_queue_meetings_calendar(config["start_month"], config["start_year"], config["end_month"],
                                     config["end_year"], queue)

    logger.info(f"Scraping meetings and documents with {num_threads} threads ...")
    processors = []
    pool = multiprocessing.Pool(num_threads)
    for i in range(num_threads):
        processors.append(pool.apply_async(processor, (queue, config, loglevel, 5, lock)))

    try:
        [p.get() for p in processors]
    except KeyboardInterrupt:
        exit(1)

    logger.info(f"Scraping done in {time.time() - start}s")


if __name__ == '__main__':
    args = parse_args()
    config = parse_config_and_args("../config.yaml", args)
    loglevel = logging.INFO
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(loglevel))

    # create tables once if required
    if config["database_url"] == "sqlite:///:memory:":
        logger.warning("!!! Writing to in-memory database! Nothing will be saved !!!")
    db = Schema(config["database_url"], verbose=False)

    if config["scrape"]:
        scrape(config)
