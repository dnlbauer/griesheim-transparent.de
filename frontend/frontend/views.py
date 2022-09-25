import logging

from django.views.generic import TemplateView

from django.shortcuts import render

from frontend import settings
from frontend.solr import SolrService

logger = logging.getLogger(__name__)


def base_context():
    return {
        "DEBUG": settings.DEBUG
    }


class MainView(TemplateView):
    template_name = "main.html"

    def get(self, request, **kwargs):
        context = base_context()

        query = request.GET.get("query", None)
        if query is not None:
            result = SolrService().search(query)
        else:
            result = None
        context['result'] = result

        return render(request, self.template_name, context=context)