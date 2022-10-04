from datetime import datetime

import math

import pysolr

from frontend import settings


class SearchResult:
    def __init__(self, title, highlight, link, download_link,
                 doc_type, short_name, date):
        self.title = title
        self.highlight = highlight
        self.link = link
        self.download_link = download_link
        self.doc_type = doc_type
        self.short_name = short_name
        self.date = date


class SearchResults:
    def __init__(self, documents, page, rows, hits, qtime):
        self.documents = documents
        self.page = page
        self.max_page = math.ceil(hits/rows)
        self.hits = hits
        self.qtime = qtime

    def __iter__(self):
        return iter(self.documents)

    def __len__(self):
        return len(self.documents)

    @property
    def has_previous(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.max_page


class SolrService:

    solr = pysolr.Solr(f"{settings.SOLR_HOST}/{settings.SOLR_COLLECTION}")

    NUM_ROWS = 10

    SOLR_ARGS = {
        "search_handler": "/select",
        "fl": "id,content,content_ocr"
    }

    HL_ARGS = {
        "hl.tag.pre": "<strong>",
        "hl.tag.post": "</strong>",
        "hl.method": "unified",
        "hl.snippets": "2",
        "hl.fragsize": "5",
        "hl.fragsizeIsMinimum": "false",
        "hl.encoder": "html",
        "hl.tag.ellipsis": "…",
        "hl.bs.type": "SEPARATOR",
        "hl.bs.separator": ".",
    }

    def _parse_search_result(self, doc, response):
        download_link = f"https://sessionnet.krz.de/griesheim/bi/getfile.asp?id={doc['document_id']}"
        if "consultation_id" in doc:
            link = f"https://sessionnet.krz.de/griesheim/bi/vo0050.asp?__kvonr={doc['consultation_id']}"
            title = doc['consultation_topic']
            doc_type = doc['consultation_type']
            short_name = doc['consultation_name']
        else:
            link = download_link
            if "content" in doc:
                title = doc['content'][:100] + "..."
            elif "content_ocr" in doc:
                title = doc['content_ocr'][:100] + "..."
            else:
                title = None
            if ("content" in doc and "niederschrift" in doc['content'][:200].lower()) or ("content_ocr" in doc and "niederschrift" in doc['content_ocr'][:200].lower()):
                doc_type = "Niederschrift"
            else:
                doc_type = None

            if "meeting_title_short" in doc and len(doc['meeting_title_short']) == 1:
                short_name = doc['meeting_title_short'][0]
            else:
                short_name = None

        if "meeting_date" in doc and len(doc['meeting_date']) > 0:
            date = sorted(doc['meeting_date'])[0]
            date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
        else:
            date = None

        hl = response.highlighting[doc['id']]
        if len(hl) > 0:
            values = [item for sublist in hl.values() for item in sublist]
            hl = "...".join(values)
        else:
            hl = None

        return SearchResult(
            title,
            hl,
            link,
            download_link,
            doc_type,
            short_name,
            date
        )

    def solr_page(self, page_number, rows_per_page):
        start = page_number * rows_per_page
        return {
            "rows": rows_per_page,
            "start": start
        }

    def search(self, query, page, hl=True):
        args = self.SOLR_ARGS
        args |= self.solr_page(page-1, self.NUM_ROWS)
        if hl:
            args |= self.HL_ARGS
        else:
            args['hl'] = 'false'
        result = self.solr.search(query, **self.SOLR_ARGS)
        documents = [self._parse_search_result(doc, result) for doc in result.docs]

        return SearchResults(documents, page, self.NUM_ROWS, result.hits, result.qtime)


