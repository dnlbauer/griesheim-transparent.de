from datetime import datetime
from enum import Enum

import math

import pysolr

from frontend import settings


def pairwise(iterable):
    return list(zip(iterable[0::2], iterable[1::2]))

class SortOrder(Enum):
    relevance = "relevance"
    date = "date"

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
    def __init__(self, documents, facets, page, rows, hits, qtime):
        self.documents = documents
        self.facets = facets
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
        "hl.encoder": "html",
        "hl.tag.pre": "<strong>",
        "hl.tag.post": "</strong>",
        "hl.fl": "content content_ocr consultation_text",
        "hl.method": "unified",
        "hl.snippets": "3",
        "hl.fragsize": "250",
        "hl.fragsizeIsMinimum": "true",
        "hl.tag.ellipsis": "…",
        "hl.bs.type": "WORD",
        "hl.defaultSummary": "true",
    }

    FACET_ARGS = {
        "facet": "true",
        "facet.field": "consultation_type_s",
    }

    def _parse_highlights(self, highlights):
        if highlights is None or len(highlights) == 0:
            return None

        hl = []
        if "consultation_text" in highlights:
            hl += highlights['consultation_text']
        if "content" in highlights:
            hl += highlights['content']
        elif "content_ocr" in highlights:
            hl += highlights['content_ocr']
        hl = "...".join(hl)
        return hl


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

        date = doc['last_seen']
        date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")

        hl = self._parse_highlights(response.highlighting[doc['id']])

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

    def search(self, query, sort, page, hl=True, facet=True):
        args = self.SOLR_ARGS
        args |= self.solr_page(page-1, self.NUM_ROWS)
        if sort == SortOrder.date:
            args['sort'] = "last_seen desc"
        else:
            args['sort'] = "score desc"
        if hl:
            args |= self.HL_ARGS
        else:
            args['hl'] = 'false'
        if facet:
            args |= self.FACET_ARGS
            args |= {"fq": query}
        result = self.solr.search(query, **self.SOLR_ARGS)

        documents = [self._parse_search_result(doc, result) for doc in result.docs]

        return SearchResults(documents, None, page, self.NUM_ROWS, result.hits, result.qtime)


