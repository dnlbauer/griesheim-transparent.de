import json
import urllib

from django.conf import settings
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceUnavailable


class TikaHealthCheckBackend(BaseHealthCheckBackend):
    critical_service = True

    def identifier(self):
        return "Tika"

    def check_status(self):
        url = self._get_healthcheck_url()
        try:
            r = urllib.request.urlopen(url)
            if r.status != 200:
                raise ServiceUnavailable(f"Unavailable (status={r.status})")

            content = r.read().decode("utf-8")
            if "Apache Tika" not in content:
                raise ServiceUnavailable(f"Status: {content}")
        except Exception as e:
            raise ServiceUnavailable(str(e))

    def _get_healthcheck_url(self):
        host = settings.TIKA_HOST
        if host.endswith("/"):
            host = host[:-1]
        return f"{host}/version"
