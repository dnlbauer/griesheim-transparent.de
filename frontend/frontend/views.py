import base64
import logging

from django.contrib.auth import authenticate
from django.core.management import call_command
from django.http import HttpResponse
from django.views.generic import TemplateView

from django.shortcuts import render, redirect

from frontend import settings
from frontend import solr
from .models import Query
from .solr import suggest, SortOrder

logger = logging.getLogger(__name__)


def base_context():
    return {
        "DEBUG": settings.DEBUG
    }


def parse_page(request, default=1):
    page = request.GET.get("page", default)
    if type(page) != int and not page.isnumeric():
        return default
    else:
        page = int(page)
        if page < 1:
            return 1
        else:
            return page


def is_auth(request):
    if "HTTP_AUTHORIZATION" in request.META:
        auth = request.META["HTTP_AUTHORIZATION"].split()
        if len(auth) == 2 and auth[0] == "Basic":
            username, passwd = base64.b64decode(auth[1]).decode("utf-8").split(":")
            user = authenticate(username=username, password=passwd)
            return user is not None and user.is_superuser and user.is_active
    return False


def update(request):
    if is_auth(request):
        chunk_size = int(request.GET.get("chunk_size", 10))
        call_command("update_solr", chunk_size=chunk_size)
        return HttpResponse("ok", content_type="text/plain")
    return HttpResponse("Unauthorized", status=401, content_type="text/plain")


class MainView(TemplateView):
    template_name = "main/main.html"
    autofocus = True

    def get(self, request, **kwargs):
        context = base_context()

        query = request.GET.get("query", None)
        sort = solr.SortOrder(request.GET.get("sort", "relevance"))
        doc_type = request.GET.get("doc_type", "*")
        organization = request.GET.get("organization", "*")
        page = parse_page(request, 1)
        if query is not None:
            Query(query=query).save()
            result = solr.search(query, page, sort, facet_filter=dict(doc_type=doc_type, organization=organization))
        else:
            context['num_docs'] = solr.search("*:*").hits
            result = solr.search("*:*", sort=SortOrder.date, limit=5)

        context['query'] = query
        context['organization'] = organization
        context['doc_type'] = doc_type
        context['sort'] = sort.value
        context['result'] = result
        context['autofocus'] = self.autofocus
        return render(request, self.template_name, context=context)


class SearchView(MainView):
    template_name = "search/search.html"
    autofocus = False

    def get(self, request, **kwargs):
        query = request.GET.get("query", None)
        if query is None or len(query) == 0:
            return redirect("main")
        else:
            return super().get(request, **kwargs)

class SuggestView(TemplateView):
    template_name = "components/suggestions.html"

    def get(self, request, **kwargs):
        query = request.GET.get("query", None)
        if query is None:
            suggestions = []
        else:
            suggestions = suggest(query)
        status = 200
        if (len(suggestions) == 0):
            status = 404
        return render(request, self.template_name, context={"suggestions": suggestions}, status=status)

