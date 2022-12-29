import math

class SearchResult:
    def __init__(self, id, document_id, title, organization, highlight, link, download_link,
                 doc_type, short_name, date, preview_image):
        self.id = id
        self.document_id = document_id
        self.title = title
        self.organization = organization
        self.highlight = highlight
        self.link = link
        self.download_link = download_link
        self.doc_type = doc_type
        self.short_name = short_name
        self.date = date
        self.preview_image = preview_image

class SearchResults:
    def __init__(self, documents, facets, page, rows, hits, qtime,
                 spellcheck_suggested_query=None, spellcheck_suggested_query_hits=None):
        self.documents = documents
        self.facets = facets
        self.page = page
        self.max_page = math.ceil(hits/rows)
        self.hits = hits
        self.qtime = qtime
        self.spellcheck_suggested_query = spellcheck_suggested_query
        self.spellcheck_suggested_query_hits = spellcheck_suggested_query_hits

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
