import logging

from django.views.generic import TemplateView

from frontend.models import Document
from django.shortcuts import render

logger = logging.getLogger(__name__)

def get_docs(query):
    docs = None
    if query is not None:
        docs = [
            Document("test", query),
            Document("test2", "test")
        ]
    return docs

class MainView(TemplateView):
    template_name = "main.html"

    def get(self, request, **kwargs):
        query = request.GET.get("query", None)
        docs = get_docs(query)

        return render(request, self.template_name, context={"documents": docs})

class SearchView(TemplateView):
    template_name = "search/search.html"

    def get(self, request, **kwargs):
        query = request.GET.get("query", None)
        docs = get_docs(query)

        return render(request, self.template_name, context={'documents': docs})