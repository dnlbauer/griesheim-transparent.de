import logging

from django.views.generic import TemplateView

from django.shortcuts import render

from frontend.solr import SolrService

logger = logging.getLogger(__name__)


class MainView(TemplateView):
    template_name = "main.html"

    def get(self, request, **kwargs):
        query = request.GET.get("query", None)
        result = SolrService().search(query)

        return render(request, self.template_name, context={"result": result})


class SearchView(TemplateView):
    template_name = "search/search.html"

    def get(self, request, **kwargs):
        query = request.GET.get("query", None)
        result = SolrService().search(query)

        return render(request, self.template_name, context={"result": result})
