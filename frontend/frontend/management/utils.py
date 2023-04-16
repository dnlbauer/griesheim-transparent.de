import base64

import requests
from django.conf import settings
from tika import parser

from ris.models import Document


def get_preview_image_for_doc(path):
    """ Perform a request against the external preview image service
    to generate a preview thumbnail for the document """

    binary = open(path, "rb").read()

    url = f"{settings.PREVIEW_HOST}/preview/{settings.PREVIEW_RESOLUTION}"
    response = requests.post(url, files=dict(file=binary))

    if response.status_code == 200:
        image_base64 = base64.b64encode(response.content).decode("utf-8")
        return f"data:image/jpeg;base64, {image_base64}"
    else:
        print(f"Failed to generate preview image for document (id={path})")
        return None

def analyze_document_tika(path, ocr=False):
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

    parsed = parser.from_file(
        path,
        serverEndpoint=settings.TIKA_HOST,
        headers=headers,
        requestOptions={'timeout': 30*60}
    )

    return parsed

def analyze_document_pdfact(path):
    """ Analyze document with pdfact and return the whole text """

    binary = open(path, "rb").read()

    response = requests.post(url=f"{settings.PDFACT_HOST}/analyze", files=dict(file=binary))
    if response.status_code != 200:  # something went wrong
        print("Failed to extract text using pdfact.")
        return None

    # parse response
    json = response.json()
    snippets = []
    for paragraph in json["paragraphs"]:
        snippets.append(paragraph["paragraph"]["text"])
    if len(snippets) == 0:
        print("pdfact returned no text")
        return None
    return snippets


