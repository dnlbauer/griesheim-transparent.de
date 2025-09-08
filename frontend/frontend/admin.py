from django.apps import apps
from django.contrib import admin
from django.db import models

from frontend.models import Query


@admin.register(Query)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "user",
        "query",
        "num_results",
        "query_time",
        "organization",
        "doc_type",
        "sort",
        "page",
    )
    list_filter = ("date", "user", "query", "organization", "doc_type", "sort", "page")
    search_fields = ["query"]


def create_model_admin(model):
    """Auto-generate admin class with list_display and filters"""

    list_display_fields = []
    list_filter_fields = []
    search_fields = []

    for field in model._meta.fields:
        field_name = field.name
        list_display_fields.append(field_name)

        # Add text and id fields to search_fields
        if (
            isinstance(field, models.CharField | models.TextField)
            or field_name == "id"
            or field_name.endswith("id")
        ):
            search_fields.append(field_name)

        # Add filterable fields
        if isinstance(
            field, models.BooleanField | models.DateTimeField | models.ForeignKey
        ):
            list_filter_fields.append(field_name)

    # Create admin class dynamically
    admin_class = type(
        f"{model.__name__}Admin",
        (admin.ModelAdmin,),
        {
            "list_display": tuple(list_display_fields) or ("__str__",),
            "list_filter": tuple(list_filter_fields),
            "search_fields": search_fields,
        },
    )

    return admin_class


# Auto-discover and register all RIS models with generated admin classes
ris_app = apps.get_app_config("ris")
for model in ris_app.get_models():
    if not model._meta.abstract:
        admin.site.register(model, create_model_admin(model))
