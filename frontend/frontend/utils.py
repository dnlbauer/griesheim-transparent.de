import base64

import requests
from django.conf import settings

from frontend.risdb.models import Document


def get_preview_image_for_doc(document_id):
    doc = Document.objects.get(document_id=int(document_id))
    url = f"{settings.PREVIEW_HOST}/preview/{settings.PREVIEW_RESOLUTION}"
    session = requests.Session()
    response = session.post(url, files=dict(file=doc.content_binary))
    if response.status_code == 200:
        response_content = response.content
        response_content = base64.b64encode(response_content).decode('utf-8')
        response_content = "data:image/jpeg;base64, " + response_content
        return response_content
    else:
        print(f"Failed to generate preview image for document (id={document_id})")
        return None
