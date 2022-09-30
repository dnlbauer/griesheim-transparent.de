import pysolr

from frontend import settings


def pairwise(iterable):
    return list(zip(iterable[0::2], iterable[1::2]))


class SearchResults:
    def __init__(self, documents, facets, hits, qtime):
        self.documents = documents
        self.facets = facets
        self.hits = hits
        self.qtime = qtime


class SolrService:

    solr = pysolr.Solr(f"{settings.SOLR_HOST}/{settings.SOLR_COLLECTION}")

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

    FACET_ARGS = {
        "facet": "true",
        "facet.field": "consultation_type_s",
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

    def search(self, query, hl=True, facet=True):
        args = self.SOLR_ARGS
        if hl:
            args |= self.HL_ARGS
        else:
            args['hl'] = 'false'
        if facet:
            args |= self.FACET_ARGS
            args |= {"fq": query}
        result = self.solr.search(query, **self.SOLR_ARGS)
        documents = [self._parse_document(doc, result) for doc in result.docs]
        if facet:
            facets = {
                "consultation_type": pairwise(result.facets['facet_fields']['consultation_type_s'])
            }
        else:
            facets = {}

        return SearchResults(documents, facets, result.hits, result.qtime)


