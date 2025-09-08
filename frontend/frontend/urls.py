"""frontend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls import handler400, handler403, handler404, handler500
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

from frontend.views import MainView, SearchView, SuggestView, update

urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(r"healthcheck", include("health_check.urls")),
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

if not settings.DEBUG:
    handler400 = "frontend.views.handler_400"
    handler403 = "frontend.views.handler_403"
    handler404 = "frontend.views.handler_404"
    handler500 = "frontend.views.handler_500"
