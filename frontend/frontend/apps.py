from django.apps import AppConfig
from health_check.plugins import plugin_dir
from frontend.healthcheck import *

class MyAppConfig(AppConfig):
    name = "frontend"

    def ready(self):
        plugin_dir.register(SolrHealthCheckBackend)
        plugin_dir.register(PreviewServiceHealthCheckBackend)
        plugin_dir.register(TikaHealthCheckBackend)
        plugin_dir.register(PDFActHealthCheckBackend)
        plugin_dir.register(GotenbergHealthCheckBackend)
