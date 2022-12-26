from datetime import datetime
from enum import Enum

from frontend.search import SearchResult, SearchResults
from frontend.search.utils import pairwise, solr_page, solr_connection

# default number of documents to return
NUM_ROWS = 10

# settings to pass to solr
SOLR_ARGS = {
    "search_handler": "/select",
    "fl": "id,first_seen,preview_image"
}

# facet specific settings
FACET_FIELDS = {
    "doc_type": "doc_type",
    "organization": "meeting_organization_name_s"
}

FACET_ARGS = {
    "facet": "true",
    "facet.field": ["{!ex=facetignore}" + i for i in FACET_FIELDS.values()],
    "facet.missing": "false",
    "facet.sort": "count",
    "facet.mincount": 1
}

# highlighting
HL_FIELDS = "doc_title consultation_topic consultation_text content_hp content content_hr"  # order matters!
HL_MAX_SNIPPETS = 3

HL_ARGS = {
    "hl": "true",
    "hl.encoder": "html",
    "hl.tag.pre": "<strong>",
    "hl.tag.post": "</strong>",
    "hl.fl": HL_FIELDS,
    "hl.method": "unified",
    "hl.bs.country": "DE",
    "hl.bs.language": "de",
    "hl.bs.type": "LINE",
    "hl.mergeContiguous": "false",
    "hl.snippets": HL_MAX_SNIPPETS,
    "hl.maxMultiValuedToMatch": HL_MAX_SNIPPETS,
    "hl.fragsize": "250",
    "hl.fragsizeIsMinimum": "false",
    "hl.defaultSummary": "false",
    "hl.requireFieldMatch": "true"
}

# highlighting for landing page
HL_NEWEST_ARGS = {
    "hl": "true",
    "hl.encoder": "html",
    "hl.fl": "content",
    "hl.bs.country": "DE",
    "hl.bs.language": "de",
    "hl.bs.type": "LINE",
    "hl.fragsize": "100000",
    "hl.snippets": "2147483647",
    "hl.defaultSummary": "true",
}



class SortOrder(Enum):
    relevance = "relevance"
    date = "date"


def _parse_highlights(highlights, max_len, separator=" "):
    # remove empty string highlights
    for key in highlights:
        non_empty = [hl for hl in highlights[key] if hl.strip()]
        if len(non_empty) > 0:
            highlights[key] = non_empty
        else:
            del highlights[key]

    # concatenate highlights into a single string with max_len
    # as a soft limit (stopping once max_len is exceeded)
    def highlight2str(highlights):
        hl = ""
        for field in HL_FIELDS.split(" "):
            if hl:
                return hl
            elif field in highlights:
                for frag in highlights[field]:
                    if hl:
                        hl += separator + frag
                    else:
                        hl = frag
                    if len(hl) > max_len:
                        return hl
        return hl
    hl = highlight2str(highlights)

    if hl:
        # append the seperator if the sentence is not finished
        if not hl.strip().endswith("."):
            hl += separator.rstrip()
        return hl
    return None


def _parse_search_result(doc, response):
    id = doc["id"]
    document_id = doc["document_id"]
    download_link = f"https://sessionnet.krz.de/griesheim/bi/getfile.asp?id={document_id}"

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

    # result title depends on the document type.
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

    # doc date is set to the first time we found an event associated with this doc
    if "first_seen" in doc:
        date = doc['first_seen']
        date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
    else:
        date = None

    if response.highlighting and doc['id'] in response.highlighting:
        hl = _parse_highlights(response.highlighting[doc['id']], max_len=200, separator=" … ")
    else:
        hl = None

    if "preview_image" in doc:
        preview_image = doc['preview_image']
    else:
        preview_image = None

    return SearchResult(
        id,
        document_id,
        title,
        hl,
        link,
        download_link,
        doc_type,
        short_name,
        date,
        preview_image
    )

SUGGEST_ARGS = {
    "suggest": "true",
}

def _parse_facets(facets):
    parsed_results = {}
    if "facet_fields" in facets:
        for name in FACET_FIELDS:
            field_name = FACET_FIELDS[name]
            if field_name in facets['facet_fields']:
                parsed_results[name] = pairwise(facets['facet_fields'][field_name])
    return parsed_results

def _create_solr_args(query, page, sort, limit, facet_filter, hl, facet):
    """ parses the set of solr arguments to a single dictionary matching the query """
    args = dict(SOLR_ARGS)

    # sort order
    if sort == SortOrder.date:
        args['sort'] = "first_seen desc"
    else:
        args['sort'] = "score desc"

    # filter documents based on selected facets
    fq = list(filter(lambda fq: fq[-2] != "*", map(lambda name: "{!tag=facetignore}"f"{FACET_FIELDS[name]}:\"{facet_filter[name]}\"", facet_filter.keys())))
    if len(fq) > 0:
        args['fq'] = fq

    # highlighting
    if hl:
        args |= HL_ARGS
    else:
        args['hl'] = 'false'

    # faceting
    if facet:
        args |= FACET_ARGS
        args['facet.query'] = query

    # rows / paging
    if limit is not None:
        args['rows'] = int(limit)
    else:
        args['rows'] = NUM_ROWS
    args |= solr_page(page-1, args['rows'])

    return args

def count(query, solr_conn=solr_connection()):
    """ get a count of documents matching the query """
    result = solr_conn.search(query, rows=0)
    return result.hits


def search(query, page=1, sort=SortOrder.relevance, limit=None, facet_filter=None, hl=True, facet=True, solr_conn=solr_connection()):
    """ perform a search request """
    if facet_filter is None:
        facet_filter = {}
    args = _create_solr_args(query, page, sort, limit, facet_filter, hl, facet)
    result = solr_conn.search(query, **args)

    documents = [_parse_search_result(doc, result) for doc in result.docs]
    facets = _parse_facets(result.facets)

    return SearchResults(documents, facets, page, NUM_ROWS, result.hits, result.qtime)

# same as `search` but fills highlight with content
def doc_id(query="*:*", limit=5, solr_conn=solr_connection()):
    """ Search for newest documents for this query. Defaults to all documents """
    page = 1

    args = _create_solr_args(query, page, SortOrder.date, limit, {}, False, False)
    args |= HL_NEWEST_ARGS  # set HL to get an extraction of the content

    result = solr_conn.search(query, **args)

    documents = [_parse_search_result(doc, result) for doc in result.docs]
    # For newest, we want to concatenate highlighting data up to a max. len
    for doc in documents:
        doc.highlight = _parse_highlights(result.highlighting[doc.id], max_len=10000, separator=" ")
    facets = {}

    return SearchResults(documents, facets, page, NUM_ROWS, result.hits, result.qtime)

def suggest(query, solr_conn=solr_connection('/suggest')):
    """ Get search suggestions for the given query """
    response = solr_conn.search(query, **SUGGEST_ARGS)
    suggestions = response.raw_response['suggest']['default'][query]['suggestions']
    return list(map(lambda s: s['term'], suggestions))

