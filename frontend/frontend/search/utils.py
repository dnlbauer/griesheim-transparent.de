import pysolr
from django.conf import settings


def pairwise(iterable):
    """ converts a list to a list of pairs """
    return list(zip(iterable[0::2], iterable[1::2]))

def solr_connection(handler='/select'):
    """ connect to solr """
    return pysolr.Solr(f"{settings.SOLR_HOST}/{settings.SOLR_COLLECTION}", search_handler=handler)

def solr_page(page_number, rows_per_page):
    """ calculate paging parameters from query"""
    start = page_number * rows_per_page
    return {
        "rows": rows_per_page,
        "start": start
    }


