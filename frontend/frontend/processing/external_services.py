import base64
import json

import requests
import tika
from django.conf import settings
from tika import parser

from frontend.processing.cache_repository import CacheRepository
from frontend.processing.file_repository import FileRepository

cache = CacheRepository()
files = FileRepository()

# Force tika to use an external service
tika.TikaClientOnly = True


class ExternalServiceUnsuccessfulException(Exception):
    pass


def get_preview_image_for_doc(file_path, skip_cache=False):
    """ Perform a request against the external preview image service
    to generate a preview thumbnail for the document """

    if not skip_cache:
        cached = cache.get_cache_content(file_path, "preview")
        if cached:
            return cached

    binary = files.get_file_content(file_path)

    url = f"{settings.PREVIEW_HOST}/preview/{settings.PREVIEW_RESOLUTION}"
    response = requests.post(url, files=dict(file=binary))

    if response.status_code == 200:
        image_base64 = base64.b64encode(response.content).decode("utf-8")
        image_base64 = f"data:image/jpeg;base64, {image_base64}"
        cache.insert_in_cache(file_path, "preview", image_base64)
        return image_base64
    else:
        raise ExternalServiceUnsuccessfulException(f"Failed to get preview image for {file_path}")


def analyze_document_tika(file_path, ocr=False, skip_cache=False):
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
        cached = cache.get_cache_content(file_path, f"tika{'.ocr' if ocr else ''}")
        if cached:
            return json.loads(cached)

    parsed = parser.from_file(
        files.get_file_path(file_path),
        serverEndpoint=settings.TIKA_HOST,
        headers=headers,
        requestOptions={'timeout': 30 * 60}
    )
    if parsed:
        cache.insert_in_cache(file_path, f"tika{'.ocr' if ocr else ''}", json.dumps(parsed, indent=4))
        return parsed
    else:
        raise ExternalServiceUnsuccessfulException(f"Failed to process document with tika: {file_path}")


def analyze_document_pdfact(file_path, skip_cache=False):
    """ Analyze document with pdfact and return the whole text """

    def is_valid_response(response):
        return response and len(response) > 0

    if not skip_cache:
        cached = cache.get_cache_content(file_path, "pdfact")
        if cached:
            content = json.loads(cached)
            if is_valid_response(content):
                return content
            else:
                raise ExternalServiceUnsuccessfulException("pdfact returned no text")

    binary = files.get_file_content(file_path)

    response = requests.post(url=f"{settings.PDFACT_HOST}/analyze", files=dict(file=binary))
    if response.status_code != 200:  # something went wrong
        raise ExternalServiceUnsuccessfulException(f"Failed to extract text using pdfact: {file_path}")

    # parse response
    json_response = response.json()
    snippets = []
    for paragraph in json_response["paragraphs"]:
        snippets.append(paragraph["paragraph"]["text"])

    cache.insert_in_cache(file_path, "pdfact", json.dumps(snippets, indent=4))
    if is_valid_response(snippets):
        return snippets
    else:
        raise ExternalServiceUnsuccessfulException("pdfact returned no text")


def convert_to_pdf(file_path, skip_cache=False):
    if not skip_cache and cache.exists_in_cache(file_path, "converted.pdf"):
        return cache.get_cache_file_path(file_path, "converted.pdf")

    form_data = {"files": files.open_file(file_path, "rb")}
    response = requests.post(url=f"{settings.GOTENBERG_HOST}/forms/libreoffice/convert", files=form_data)
    if response.status_code != 200:  # something went wrong
        raise ExternalServiceUnsuccessfulException("Failed to convert document to pdf.")

    content = response.content
    return cache.insert_in_cache(file_path, "converted.pdf", content, mode="wb")
