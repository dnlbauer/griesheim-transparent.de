import pysolr

from frontend import settings


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

    def search(self, query, hl=True):
        args = self.SOLR_ARGS
        if hl:
            args |= self.HL_ARGS
        else:
            args['hl'] = 'false'
        return self.solr.search(query, **self.SOLR_ARGS)

