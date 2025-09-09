from django.apps import AppConfig
from health_check.plugins import plugin_dir

from healthcheck import (
    GotenbergHealthCheckBackend,
    PDFActHealthCheckBackend,
    PreviewServiceHealthCheckBackend,
    SolrHealthCheckBackend,
    TikaHealthCheckBackend,
)


class HealthCheckConfig(AppConfig):
    name = "healthcheck"

    def ready(self) -> None:
        plugin_dir.register(SolrHealthCheckBackend)
        plugin_dir.register(PreviewServiceHealthCheckBackend)
        plugin_dir.register(TikaHealthCheckBackend)
        plugin_dir.register(PDFActHealthCheckBackend)
        plugin_dir.register(GotenbergHealthCheckBackend)
