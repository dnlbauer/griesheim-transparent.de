import logging

from django.views.generic import TemplateView

from django.shortcuts import render, redirect

from frontend import settings
from frontend import solr
from solr import suggest

logger = logging.getLogger(__name__)


def base_context():
    return {
        "DEBUG": settings.DEBUG
    }


def parse_page(request):
    page = request.GET.get("page", "1")
    if not page.isnumeric():
        return 1
    else:
        page = int(page)
        if page < 1:
            return 1
        else:
            return page


class MainView(TemplateView):
    template_name = "main.html"

    def get(self, request, **kwargs):
        context = base_context()

        query = request.GET.get("query", None)
        sort = solr.SortOrder(request.GET.get("sort", "relevance"))
        doc_type = request.GET.get("doc_type", "*")
        organization = request.GET.get("organization", "*")
        page = parse_page(request)
        if query is not None:
            result = solr.search(query, page, sort, facet_filter=dict(doc_type=doc_type, organization=organization))
        else:
            result = []
            context['num_docs'] = solr.search("*:*").hits

        context['query'] = query
        context['organization'] = organization
        context['doc_type'] = doc_type
        context['sort'] = sort.value
        context['result'] = result

        return render(request, self.template_name, context=context)


class SearchView(MainView):
    template_name = "search/search.html"

    def get(self, request, **kwargs):
        query = request.GET.get("query", None)
        if query is None or len(query) == 0:
            return redirect("main")
        else:
            return super().get(request, **kwargs)

class SuggestView(TemplateView):
    template_name = "suggestions.html"

    def get(self, request, **kwargs):
        query = request.GET.get("query", None)
        if query is None:
            suggestions = []
        else:
            suggestions = suggest(query)
        return render(request, self.template_name, context={"suggestions": suggestions})

