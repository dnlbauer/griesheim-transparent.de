import json
import urllib.request

from django.conf import settings
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceUnavailable


class SolrHealthCheckBackend(BaseHealthCheckBackend):
    critical_service = True

    def identifier(self) -> str:
        return "Solr"

    def check_status(self) -> None:
        url = self._get_healthcheck_url()
        try:
            r = urllib.request.urlopen(url)
            if r.status != 200:
                raise ServiceUnavailable(f"Unavailable (status={r.status})")

            content = json.loads(r.read().decode("utf-8"))
            status = content["status"]
            if status != "OK":
                raise ServiceUnavailable(f"Status: {status}")
        except Exception as e:
            raise ServiceUnavailable(f"{url}: {str(e)}") from e

    def _get_healthcheck_url(self) -> str:
        host = settings.SOLR_HOST
        if host.endswith("/"):
            host = host[:-1]
        return f"{host}/{settings.SOLR_COLLECTION}/admin/ping?wt=json"
