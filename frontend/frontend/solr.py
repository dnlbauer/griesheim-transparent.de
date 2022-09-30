import math

import pysolr

from frontend import settings


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
        "fl": "id,consultation_id",
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

    def _parse_document(self, doc, response):
        hl = response.highlighting[doc['id']]
        if len(hl) > 0:
            values = [item for sublist in hl.values() for item in sublist]
            doc["hl"] = "...".join(values)
        doc['download'] = f"https://sessionnet.krz.de/griesheim/bi/getfile.asp?id={doc['document_id']}"
        if "consultation_id" in doc:
            doc["link"] = f"https://sessionnet.krz.de/griesheim/bi/vo0050.asp?__kvonr={doc['consultation_id']}"
        else:
            doc["link"] = doc['download']
        return doc

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
        documents = [self._parse_document(doc, result) for doc in result.docs]

        return SearchResults(documents, page, self.NUM_ROWS, result.hits, result.qtime)


