from os.path import join
from typing import IO, Any, cast

from django.conf import settings


class FileRepository:
    def __init__(self) -> None:
        self.base_path = settings.DOCUMENT_STORE

    def get_file_path(self, uri: str) -> str:
        return join(self.base_path, uri)

    def open_file(self, uri: str, mode: str = "rb") -> IO[Any]:
        return open(self.get_file_path(uri), mode)

    def get_file_content(self, uri: str, mode: str = "rb") -> str | bytes:
        if "b" in mode:
            return cast(bytes, self.open_file(uri, mode).read())
        else:
            return cast(str, self.open_file(uri, mode).read())
