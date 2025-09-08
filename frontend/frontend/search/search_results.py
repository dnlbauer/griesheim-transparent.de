import math
from collections.abc import Iterator
from datetime import datetime

type Facet = tuple[str, int]  # facet value to count
type Facets = dict[str, list[Facet]]  # facet name to list of facets


class SearchResult:
    def __init__(
        self,
        id: str,
        document_id: str,
        title: str | None,
        organization: str | None,
        highlight: str | None,
        link: str | None,
        download_link: str,
        doc_type: str | None,
        short_name: str | None,
        date: datetime | None,
        preview_image: str | None,
        filetype: str | None,
    ) -> None:
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
        self.filetype = filetype


class SearchResults:
    def __init__(
        self,
        documents: list[SearchResult],
        facets: Facets,
        page: int,
        rows: int,
        hits: int,
        qtime: int,
        spellcheck_suggested_query: str | None = None,
        spellcheck_suggested_query_hits: int | None = None,
    ) -> None:
        self.documents = documents
        self.facets = facets
        self.page = page
        self.max_page = math.ceil(hits / rows)
        self.hits = hits
        self.qtime = qtime
        self.spellcheck_suggested_query = spellcheck_suggested_query
        self.spellcheck_suggested_query_hits = spellcheck_suggested_query_hits

    def __iter__(self) -> Iterator[SearchResult]:
        return iter(self.documents)

    def __len__(self) -> int:
        return len(self.documents)

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.max_page
