from django.contrib import admin

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
