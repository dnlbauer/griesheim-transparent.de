import base64
import json
from os import makedirs

import requests
from django.conf import settings
from tika import parser
from os.path import basename, join, dirname


def get_cache_path(path, postfix):
    name = basename(path)
    return join(settings.CACHE_DIR, f"{name}.{postfix}")


def insert_in_cache(path, postfix, content):
    cache_path = get_cache_path(path, postfix)
    makedirs(dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        f.write(content)


def get_cache_content(path, postfix):
    try:
        with open(get_cache_path(path, postfix), "r") as f:
            return f.read()
    except FileNotFoundError:
        return None


def get_preview_image_for_doc(path, skip_cache=False):
    """ Perform a request against the external preview image service
    to generate a preview thumbnail for the document """

    if not skip_cache:
        cached = get_cache_content(path, "preview")
        if cached:
            return cached

    binary = open(path, "rb").read()

    url = f"{settings.PREVIEW_HOST}/preview/{settings.PREVIEW_RESOLUTION}"
    response = requests.post(url, files=dict(file=binary))

    if response.status_code == 200:
        image_base64 = base64.b64encode(response.content).decode("utf-8")
        image_base64 = f"data:image/jpeg;base64, {image_base64}"
        insert_in_cache(path, "preview", image_base64)
        return image_base64
    else:
        print(f"Failed to generate preview image for document (id={path})")
        return None


def analyze_document_tika(path, ocr=False, skip_cache=False):
    """ Extract document text with tika or tesseract(ocr) """

    if not ocr:
        headers = {
            "X-Tika-PDFOcrStrategy": "no_ocr",
        }
    else:
        headers = {
            "X-Tika-PDFOcrStrategy": "OCR_ONLY",
            "X-Tika-OCRLanguage": "deu",
            "X-Tika-OCRTimeout": str(30*60)
        }

    if not skip_cache:
        cached = get_cache_content(path, f"tika{'.ocr' if ocr else ''}")
        if cached:
            return json.loads(cached)

    parsed = parser.from_file(
        path,
        serverEndpoint=settings.TIKA_HOST,
        headers=headers,
        requestOptions={'timeout': 30*60}
    )
    insert_in_cache(path, f"tika{'.ocr' if ocr else ''}", json.dumps(parsed, indent=4))

    return parsed


def analyze_document_pdfact(path, skip_cache=False):
    """ Analyze document with pdfact and return the whole text """

    if not skip_cache:
        cached = get_cache_content(path, "pdfact")
        if cached:
            return json.loads(cached)

    binary = open(path, "rb").read()

    response = requests.post(url=f"{settings.PDFACT_HOST}/analyze", files=dict(file=binary))
    if response.status_code != 200:  # something went wrong
        print("Failed to extract text using pdfact.")
        return None

    # parse response
    json_response = response.json()
    snippets = []
    for paragraph in json_response["paragraphs"]:
        snippets.append(paragraph["paragraph"]["text"])
    if len(snippets) == 0:
        print("pdfact returned no text")
        return None

    insert_in_cache(path, "pdfact", json.dumps(snippets, indent=4))
    return snippets


