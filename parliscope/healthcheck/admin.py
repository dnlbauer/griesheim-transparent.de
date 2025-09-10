import logging

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import path

from frontend.search.utils import solr_connection
from models.models import Document

logger = logging.getLogger(__name__)


def get_detailed_system_health():
    """Get system health information"""
    health_data = {}

    # Database document count
    try:
        db_document_count = Document.objects.count()
        health_data["database_document_count"] = db_document_count
        health_data["database_available"] = True
    except Exception as e:
        logger.error(f"Error accessing database: {e}")
        health_data["database_document_count"] = 0
        health_data["database_available"] = False
        health_data["database_error"] = str(e)

    # Solr document count
    try:
        solr_conn = solr_connection()
        stats_query = solr_conn.search("*:*", rows=0)
        health_data["solr_document_count"] = stats_query.hits
        health_data["solr_available"] = True
    except Exception as e:
        logger.error(f"Error connecting to Solr: {e}")
        health_data["solr_document_count"] = 0
        health_data["solr_available"] = False
        health_data["solr_error"] = str(e)

    # Sync status
    if health_data["database_available"] and health_data["solr_available"]:
        db_count = health_data["database_document_count"]
        solr_count = health_data["solr_document_count"]
        health_data["sync_status"] = {
            "in_sync": db_count == solr_count,
            "difference": solr_count - db_count,
        }
    else:
        health_data["sync_status"] = {"in_sync": False, "difference": 0}

    return health_data


@staff_member_required
def system_health_view(request: HttpRequest) -> HttpResponse:
    """Dedicated system health monitoring page"""
    context = {
        "title": "System Health Overview",
        "health_data": get_detailed_system_health(),
    }
    return render(request, "healthcheck/system_health.html", context)


class HealthMonitoringAdminSite(admin.AdminSite):
    """Custom admin site with system health monitoring page"""

    def get_urls(self):
        admin_urls = super().get_urls()
        custom_urls = [
            path(
                "health/",
                self.admin_view(system_health_view),
                name="system_health",
            ),
        ]
        return custom_urls + admin_urls


# Override the default admin site class
admin.site.__class__ = HealthMonitoringAdminSite
