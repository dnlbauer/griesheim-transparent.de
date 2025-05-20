import base64
import logging
from multiprocessing import Process

from django.contrib.auth import authenticate
from django.core.management import call_command
from django.http import HttpResponse
from django.views.generic import TemplateView

from django.shortcuts import render, redirect

from frontend import settings
from .models import Query
from .search import solr

logger = logging.getLogger(__name__)

BASE_CONTEXT = {
    "DEBUG": settings.DEBUG  # config js debugging
}


def _parse_parge(request, default=1):
    """ The requested page. Defaults to first page is no or an invalid page is requested"""
    page = request.GET.get("page", default)
    if type(page) != int and not page.isnumeric():
        return default
    else:
        page = int(page)
        if page < 1:
            return 1
        else:
            return page


def _is_authenticated_su(request):
    """ True if the user is an authenticatd superuser"""
    if request.user.is_authenticated and request.user.is_superuser and request.user.is_active:
        return True

    # Check HTTP Basic Auth
    if "HTTP_AUTHORIZATION" in request.META:
        auth = request.META["HTTP_AUTHORIZATION"].split()
        if len(auth) == 2 and auth[0] == "Basic":
            username, passwd = base64.b64decode(auth[1]).decode("utf-8").split(":")
            user = authenticate(username=username, password=passwd)
            return user is not None and user.is_superuser and user.is_active
    return False



update_proc = None
def update(request):
    """ Triggers async update of the solar index (runs update_solr management task.
    Therefore, a new process is started and the view returnes immediatly.
    If the update process is already running, it gets killed and a new one
    is started """

    if _is_authenticated_su(request):
        global update_proc
        # check if update process is already running, kill it if yes
        if update_proc is not None and update_proc.is_alive():
            update_proc.kill()

        # start update in a new process
        chunk_size = int(request.GET.get("chunk_size", 10))

        def proc(chunk_size):
            call_command("update_solr", chunk_size=10)
        update_proc = Process(target=proc, args=(chunk_size,))
        update_proc.start()

        return HttpResponse("ok", content_type="text/plain")

    return HttpResponse("Unauthorized", status=401, content_type="text/plain")


class MainView(TemplateView):
    """ Landing page """
    template_name = "main/main.html"
    autofocus = True  # Focus on search input field?

    def get(self, request, **kwargs):
        context = BASE_CONTEXT

        # parse query parameters
        query = request.GET.get("query", None)
        sort = solr.SortOrder(request.GET.get("sort", "relevance"))
        doc_type = request.GET.get("doc_type", "*")
        organization = request.GET.get("organization", "*")
        page = _parse_parge(request, 1)

        # perform solr query
        if query is not None:
            result = solr.search(query, page, sort, facet_filter=dict(doc_type=doc_type, organization=organization))
            Query(
                query=query,
                user=request.user.username if request.user.is_authenticated else None,
                organization=organization,
                doc_type=doc_type,
                sort=sort,
                page=page,
                num_results=result.hits,
                query_time=result.qtime
            ).save()  # Query log
        else:
            context['num_docs'] = solr.count("*:*")
            result = solr.doc_id("*:*", limit=5)

        context['query'] = query
        context['organization'] = organization
        context['doc_type'] = doc_type
        context['sort'] = sort.value
        context['result'] = result
        context['autofocus'] = self.autofocus
        return render(request, self.template_name, context=context)


class SearchView(MainView):
    """ Search results page """
    template_name = "search/search.html"
    autofocus = False  # no autofocus on search

    def get(self, request, **kwargs):
        query = request.GET.get("query", None)

        # redirect to landing page if nothing was searched
        if query is None or len(query) == 0:
            return redirect("main")
        else:
            return super().get(request, **kwargs)

class SuggestView(TemplateView):
    """ Handler for search suggestions """
    template_name = "components/suggestions.html"

    def get(self, request, **kwargs):
        query = request.GET.get("query", None)
        if query is None:
            suggestions = []
        else:
            suggestions = solr.suggest(query)

        if (len(suggestions) > 0):
            status = 200
        else:
            status = 404

        return render(request, self.template_name, context={"suggestions": suggestions}, status=status)

def error_handler(request, code, message):
    context = dict(
        status_code=code,
        message=message
    )
    return render(request, "error.html", status=code, context=context)

def handler_400(request, *args, **kwargs):
    return error_handler(request, 400, "Ungültige Anfrage.")


def handler_403(request, *args, **kwargs):
    return error_handler(request, 403, "Zugriff verweigert.")


def handler_404(request, *args, **kwargs):
    return error_handler(request, 404, "Seite konnte nicht gefunden werden.")


def handler_500(request, *args, **kwargs):
    return error_handler(request, 500, "Serverfehler.")
