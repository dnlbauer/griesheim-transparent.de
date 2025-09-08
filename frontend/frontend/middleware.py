from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect


class RestrictUserMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path.startswith("/healthcheck"):
            if request.user.is_authenticated and request.user.is_superuser:
                return self.get_response(request)
            else:
                return redirect("/admin/login/?next=" + request.path)
        else:
            return self.get_response(request)
