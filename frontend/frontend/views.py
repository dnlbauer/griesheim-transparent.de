import logging

from django.views.generic import TemplateView

from django.shortcuts import render

from frontend.solr import SolrService

logger = logging.getLogger(__name__)

def search_documents_context(query):
    result = None
    if query:
        docs = SolrService().search(query)
        result = []
        for document in docs:
            hl = docs.highlighting[document['id']]
            if len(hl) > 0:
                values = [item for sublist in hl.values() for item in sublist]
                document["hl"] = "...".join(values)
            result.append(document)

    return dict(result=result)


class MainView(TemplateView):
    template_name = "main.html"

    def get(self, request, **kwargs):
        query = request.GET.get("query", None)
        context = search_documents_context(query)

        return render(request, self.template_name, context=context)


class SearchView(TemplateView):
    template_name = "search/search.html"

    def get(self, request, **kwargs):
        query = request.GET.get("query", None)
        context = search_documents_context(query)

        return render(request, self.template_name, context=context)