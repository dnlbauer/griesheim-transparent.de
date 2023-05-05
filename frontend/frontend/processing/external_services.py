import tika
import base64
import json

import requests
from django.conf import settings
from tika import parser

from frontend.processing.cache_repository import CacheRepository
from frontend.processing.file_repository import FileRepository

cache = CacheRepository()
files = FileRepository()

# Force tika to use an external service
tika.TikaClientOnly = True


def get_preview_image_for_doc(uri, skip_cache=False):
    """ Perform a request against the external preview image service
    to generate a preview thumbnail for the document """

    if not skip_cache:
        cached = cache.get_cache_content(uri, "preview")
        if cached:
            return cached

    binary = files.get_file_path(uri)

    url = f"{settings.PREVIEW_HOST}/preview/{settings.PREVIEW_RESOLUTION}"
    response = requests.post(url, files=dict(file=binary))

    if response.status_code == 200:
        image_base64 = base64.b64encode(response.content).decode("utf-8")
        image_base64 = f"data:image/jpeg;base64, {image_base64}"
        cache.insert_in_cache(uri, "preview", image_base64)
        return image_base64
    else:
        print(f"Failed to generate preview image for document (id={uri})")
        return None


def analyze_document_tika(uri, ocr=False, skip_cache=False):
    """ Extract document text with tika or tesseract(ocr) """

    if not ocr:
        headers = {
            "X-Tika-PDFOcrStrategy": "no_ocr",
            "X-Tika-PDFSuppressDuplicateOverlappingText": "true"
        }
    else:
        headers = {
            "X-Tika-PDFOcrStrategy": "OCR_ONLY",
            "X-Tika-OCRLanguage": "deu",
            "X-Tika-OCRTimeout": str(30 * 60)
        }

    if not skip_cache:
        cached = cache.get_cache_content(uri, f"tika{'.ocr' if ocr else ''}")
        if cached:
            return json.loads(cached)

    parsed = parser.from_file(
        files.get_file_path(uri),
        serverEndpoint=settings.TIKA_HOST,
        headers=headers,
        requestOptions={'timeout': 30 * 60}
    )
    cache.insert_in_cache(uri, f"tika{'.ocr' if ocr else ''}", json.dumps(parsed, indent=4))

    return parsed


def analyze_document_pdfact(uri, skip_cache=False):
    """ Analyze document with pdfact and return the whole text """

    if not skip_cache:
        cached = cache.get_cache_content(uri, "pdfact")
        if cached:
            return json.loads(cached)

    binary = files.get_file_content(uri)

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

    cache.insert_in_cache(uri, "pdfact", json.dumps(snippets, indent=4))
    return snippets


def convert_to_pdf(uri, skip_cache=False):
    if not skip_cache and cache.exists_in_cache(uri, "converted.pdf"):
        return cache.get_cache_file_path(uri, "converted.pdf")

    form_data = {"files": files.open(uri, "rb")}
    response = requests.post(url=f"{settings.GOTENBERG_HOST}/forms/libreoffice/convert", files=form_data)
    if response.status_code != 200:  # something went wrong
        print("Failed to convert document to pdf.")
        return None

    content = response.content
    return cache.insert_in_cache(uri, "converted.pdf", content, mode="wb")
