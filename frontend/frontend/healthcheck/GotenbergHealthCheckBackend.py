import json
import urllib

from django.conf import settings
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceUnavailable


class GotenbergHealthCheckBackend(BaseHealthCheckBackend):
    critical_service = True

    def identifier(self):
        return "Gotenberg"

    def check_status(self):
        url = self._get_healthcheck_url()
        try:
            r = urllib.request.urlopen(url)
            if r.status != 200:
                raise ServiceUnavailable(f"Unavailable (status={r.status})")

            content = json.loads(r.read().decode("utf-8"))
            if content["status"] != "up":
                raise ServiceUnavailable(f"Status: {content['status']}")
        except Exception as e:
            raise ServiceUnavailable(f"{url}: {str(e)}")

    def _get_healthcheck_url(self):
        return f"{settings.GOTENBERG_HOST}/health"
