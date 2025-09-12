import base64
import logging

from django.contrib.auth import authenticate
from django.http import HttpRequest, HttpResponse

from parliscope.tasks.indexing import update_solr_index

logger = logging.getLogger(__name__)


def _is_authenticated_su(request: HttpRequest) -> bool:
    """True if the user is an authenticated superuser"""
    if (
        request.user.is_authenticated
        and request.user.is_superuser
        and request.user.is_active
    ):
        return True

    # Check HTTP Basic Auth
    if "HTTP_AUTHORIZATION" in request.META:
        auth = request.META["HTTP_AUTHORIZATION"].split()
        if len(auth) == 2 and auth[0] == "Basic":
            username, passwd = base64.b64decode(auth[1]).decode("utf-8").split(":")
            user = authenticate(username=username, password=passwd)
            return user is not None and user.is_superuser and user.is_active
    return False


def update(request: HttpRequest) -> HttpResponse:
    """Triggers async update of the Solr index (runs update_solr management task).
    Therefore, a new process is started and the view returns immediately.
    If the update process is already running, it gets killed and a new one
    is started"""

    if _is_authenticated_su(request):
        chunk_size = int(request.GET.get("chunk_size", 10))
        update_solr_index.delay(chunk_size=chunk_size)

        return HttpResponse("ok", content_type="text/plain")

    return HttpResponse("Unauthorized", status=401, content_type="text/plain")
