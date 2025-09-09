"""frontend URL Configuration

Frontend-specific URL patterns for the parliscope project.
"""

from django.urls import path
from django.views.generic import TemplateView

from frontend.views import MainView, SearchView, SuggestView, update

urlpatterns = [
    path("update", update, name="update"),
    path("", MainView.as_view(), name="main"),
    path("search", SearchView.as_view(), name="search"),
    path("suggest", SuggestView.as_view(), name="suggest"),
    path("about", TemplateView.as_view(template_name="about.html"), name="about"),
    path("faq", TemplateView.as_view(template_name="about.html"), name="faq"),
    path(
        "impressum",
        TemplateView.as_view(template_name="impressum.html"),
        name="impressum",
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
]
