import urllib

from django.conf import settings
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceUnavailable


class PDFActHealthCheckBackend(BaseHealthCheckBackend):
    critical_service = True

    def identifier(self):
        return "Pdfact"

    def check_status(self):
        url = self._get_healthcheck_url()
        try:
            r = urllib.request.urlopen(url)
            if r.status != 200:
                raise ServiceUnavailable(f"Unavailable (status={r.status})")

            content = r.read().decode("utf-8")
            if content != "OK":
                raise ServiceUnavailable(f"Status: {content}")
        except Exception as e:
            raise ServiceUnavailable(f"{url}: {str(e)}") from e

    def _get_healthcheck_url(self):
        return settings.PDFACT_HOST
