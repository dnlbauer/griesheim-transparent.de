import re
import urllib.parse


def add_url_parameters(url, params):
    url_parts = list(urllib.parse.urlparse(url))
    query = dict(urllib.parse.parse_qsl(url_parts[4]))
    query.update(params)

    url_parts[4] = urllib.parse.urlencode(query)
    return urllib.parse.urlunparse(url_parts)


def get_url_params(url):
    parsed = urllib.parse.urlparse(url)
    return dict(urllib.parse.parse_qsl(parsed.query))


def clean_text(text):
    text = " ".join(text)
    text = re.sub("\\s+", " ", text)
    return text
