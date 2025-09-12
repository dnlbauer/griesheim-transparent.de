import logging
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.generic import TemplateView

from .models import Query
from .search import solr

logger = logging.getLogger(__name__)


def _parse_parge(request: HttpRequest, default: int = 1) -> int:
    """The requested page. Defaults to first page is no or an invalid page is requested"""
    page = request.GET.get("page", default)
    if not isinstance(page, int) and not page.isnumeric():
        return default
    else:
        page = int(page)
        if page < 1:
            return 1
        else:
            return page


class MainView(TemplateView):
    """Landing page"""

    template_name = "main/main.html"
    autofocus = True  # Focus on search input field?

    def get(self, request: HttpRequest, **kwargs: Any) -> HttpResponse:
        # TODO properly type context
        context: dict[str, Any] = {
            "DEBUG": settings.DEBUG  # config js debugging
        }

        # parse query parameters
        query = request.GET.get("query", None)
        sort = solr.SortOrder(request.GET.get("sort", "relevance"))
        doc_type = request.GET.get("doc_type", "*")
        organization = request.GET.get("organization", "*")
        page = _parse_parge(request, 1)

        # perform solr query
        if query is not None:
            result = solr.search(
                query,
                page,
                sort,
                facet_filter={"doc_type": doc_type, "organization": organization},
            )
            Query(
                query=query,
                user=request.user.username if request.user.is_authenticated else None,
                organization=organization,
                doc_type=doc_type,
                sort=sort.value,
                page=page,
                num_results=result.hits,
                query_time=result.qtime,
            ).save()  # Query log
        else:
            context["num_docs"] = solr.count("*:*")
            result = solr.doc_id("*:*", limit=5)

        context["query"] = query
        context["organization"] = organization
        context["doc_type"] = doc_type
        context["sort"] = sort.value
        context["result"] = result
        context["autofocus"] = self.autofocus
        return render(request, self.template_name, context=context)


class SearchView(MainView):
    """Search results page"""

    template_name = "search/search.html"
    autofocus = False  # no autofocus on search

    def get(self, request: HttpRequest, **kwargs: Any) -> HttpResponse:
        query = request.GET.get("query", None)

        # redirect to landing page if nothing was searched
        if query is None or len(query) == 0:
            return redirect("main")
        else:
            return super().get(request, **kwargs)


class SuggestView(TemplateView):
    """Handler for search suggestions"""

    template_name = "components/suggestions.html"

    def get(self, request: HttpRequest, **kwargs: Any) -> HttpResponse:
        query = request.GET.get("query", None)
        if query is None:
            suggestions = []
        else:
            suggestions = solr.suggest(query)

        if len(suggestions) > 0:
            status = 200
        else:
            status = 404

        return render(
            request,
            self.template_name,
            context={"suggestions": suggestions},
            status=status,
        )


def error_handler(request: HttpRequest, code: int, message: str) -> HttpResponse:
    context = {"status_code": code, "message": message}
    return render(request, "error.html", status=code, context=context)


def handler_400(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
    return error_handler(request, 400, "Ungültige Anfrage.")


def handler_403(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
    return error_handler(request, 403, "Zugriff verweigert.")


def handler_404(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
    return error_handler(request, 404, "Seite konnte nicht gefunden werden.")


def handler_500(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
    return error_handler(request, 500, "Serverfehler.")
