import re
import urllib.parse
from datetime import date


def add_url_parameters(url, params):
    url_parts = list(urllib.parse.urlparse(url))
    query = dict(urllib.parse.parse_qsl(url_parts[4]))
    query.update(params)

    url_parts[4] = urllib.parse.urlencode(query)
    return urllib.parse.urlunparse(url_parts)


def remove_url_parameters(url, params):
    url_parts = list(urllib.parse.urlparse(url))
    query = dict(urllib.parse.parse_qsl(url_parts[4]))
    for param in params:
        if param in query:
            del query[param]

    url_parts[4] = urllib.parse.urlencode(query)
    return urllib.parse.urlunparse(url_parts)


def get_url_params(url):
    parsed = urllib.parse.urlparse(url)
    return dict(urllib.parse.parse_qsl(parsed.query))


def clean_text(text):
    text = " ".join(text)
    text = re.sub("\\s+", " ", text)
    return text


def month_from_now(add=0):
    month = date.today().month
    year = date.today().year
    month += add
    while (month > 12):
        month -= 12
        year += 1
    return f"{month}/{year}"
