from os import makedirs
from os.path import basename, dirname, exists, join
from typing import cast

from django.conf import settings


class CacheRepository:
    def __init__(self) -> None:
        self.base_path = settings.CACHE_DIR

    def _uri_to_cache_path(self, uri: str, postfix: str) -> str:
        name = basename(uri)
        return join(self.base_path, f"{name}.{postfix}")

    def get_cache_file_path(self, uri: str, postfix: str) -> str | None:
        cache_path = self._uri_to_cache_path(uri, postfix)
        if exists(cache_path):
            return cache_path
        return None

    def exists_in_cache(self, uri: str, postfix: str) -> bool:
        return self.get_cache_file_path(uri, postfix) is not None

    def insert_in_cache(self, uri: str, postfix: str, content: str | bytes, mode: str = "w") -> str:
        cache_path = self._uri_to_cache_path(uri, postfix)
        makedirs(dirname(cache_path), exist_ok=True)
        with open(cache_path, mode) as f:
            f.write(content)
        return cache_path

    def get_cache_content(self, uri: str, postfix: str, mode: str = "r") -> str | bytes | None:
        if not self.exists_in_cache(uri, postfix):
            return None

        path = self.get_cache_file_path(uri, postfix)
        if not path:
            return None
        with open(path, mode) as f:
            if "b" in mode:
                return cast(bytes, f.read())
            else:
                return cast(str, f.read())
