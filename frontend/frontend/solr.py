from datetime import datetime
from enum import Enum
import math
from frontend import settings
import pysolr


def pairwise(iterable):
    return list(zip(iterable[0::2], iterable[1::2]))


class SortOrder(Enum):
    relevance = "relevance"
    date = "date"


class SearchResult:
    def __init__(self, title, highlight, link, download_link,
                 doc_type, short_name, date, preview_image):
        self.title = title
        self.highlight = highlight
        self.link = link
        self.download_link = download_link
        self.doc_type = doc_type
        self.short_name = short_name
        self.date = date
        self.preview_image = preview_image


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


NUM_ROWS = 10
FACET_FIELDS = {
    "doc_type": "doc_type",
    "organization": "meeting_organization_name_s"
}

SOLR_ARGS = {
    "search_handler": "/select",
    "fl": "id,content,content_ocr,first_seen,preview_image"
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
    "facet.field": ["{!ex=facetignore}" + i for i in FACET_FIELDS.values()],
    "facet.missing": "false",
    "facet.sort": "count",
    "facet.mincount": 1
}


def solr_connection(handler='/select'):
    return pysolr.Solr(f"{settings.SOLR_HOST}/{settings.SOLR_COLLECTION}", search_handler=handler)


def _parse_highlights(highlights):
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


def _parse_search_result(doc, response):
    download_link = f"https://sessionnet.krz.de/griesheim/bi/getfile.asp?id={doc['document_id']}"

    short_name = None
    link = None
    if "consultation_id" in doc:
        link = f"https://sessionnet.krz.de/griesheim/bi/vo0050.asp?__kvonr={doc['consultation_id']}"
        short_name = doc['consultation_name']
    elif "meeting_id" in doc:
        link = f"https://sessionnet.krz.de/griesheim/bi/si0050.asp?__ksinr={doc['meeting_id'][0]}"
        if "meeting_title_short" in doc and len(doc['meeting_title_short']) == 1:
            short_name = doc['meeting_title_short'][0]

    if "doc_type" in doc:
        doc_type = doc['doc_type']
    else:
        doc_type = "Anlage"

    title = None
    if doc_type:
        if doc_type in ["Antragsvorlage", "Beschlussvorlage", "Informationsvorlage"] and len(doc["consultation_topic"]) != 0:
            title = doc['consultation_topic']
        elif doc_type == "Niederschrift" and len(doc['meeting_title']) != 0:
            title = doc['meeting_title'][0]
    if title is None:
        if "doc_title" in doc:
            title = doc['doc_title']
        elif "content" in doc:
            title = doc['content'][:100] + "..."
        elif "content_ocr" in doc:
            title = doc['content_ocr'][:100] + "..."

    if "last_seen" in doc:
        date = doc['first_seen']
        date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
    else:
        date = None

    hl = _parse_highlights(response.highlighting[doc['id']])

    if "preview_image" in doc:
        preview_image = doc['preview_image']
    else:
        preview_image = None

    return SearchResult(
        title,
        hl,
        link,
        download_link,
        doc_type,
        short_name,
        date,
        preview_image
    )


def solr_page(page_number, rows_per_page):
    start = page_number * rows_per_page
    return {
        "rows": rows_per_page,
        "start": start
    }


def _parse_facets(facets):
    parsed_results = {}
    if "facet_fields" in facets:
        for name in FACET_FIELDS:
            field_name = FACET_FIELDS[name]
            if field_name in facets['facet_fields']:
                parsed_results[name] = pairwise(facets['facet_fields'][field_name])
    return parsed_results


def search(query, page=1, sort=SortOrder.relevance, limit=None, facet_filter={}, hl=True, facet=True, solr_conn=solr_connection()):
    args = dict(SOLR_ARGS)
    if sort == SortOrder.date:
        args['sort'] = "first_seen desc"
    else:
        args['sort'] = "score desc"
    fq = list(filter(lambda fq: fq[-2] != "*", map(lambda name: "{!tag=facetignore}"f"{FACET_FIELDS[name]}:\"{facet_filter[name]}\"", facet_filter.keys())))
    if len(fq) > 0:
        args['fq'] = fq

    if hl:
        args |= HL_ARGS
    else:
        args['hl'] = 'false'
    if facet:
        args |= FACET_ARGS
        args['facet.query'] = query
    if limit is not None:
        args['rows'] = int(limit)
    else:
        args['rows'] = NUM_ROWS
    args |= solr_page(page-1, args['rows'])

    result = solr_conn.search(query, **args)

    documents = [_parse_search_result(doc, result) for doc in result.docs]
    facets = _parse_facets(result.facets)

    return SearchResults(documents, facets, page, NUM_ROWS, result.hits, result.qtime)

def suggest(query, solr_conn=solr_connection('/suggest')):
    PARAMS = {
        "suggest": "true",
    }
    response = solr_conn.search(query, **PARAMS)
    suggestions = response.raw_response['suggest']['default'][query]['suggestions']
    return list(map(lambda s: s['term'], suggestions))

