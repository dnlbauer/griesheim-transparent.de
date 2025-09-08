from os import makedirs
from os.path import basename, dirname, exists, join

from django.conf import settings


class CacheRepository:
    def __init__(self):
        self.base_path = settings.CACHE_DIR

    def _uri_to_cache_path(self, uri, postfix):
        name = basename(uri)
        return join(self.base_path, f"{name}.{postfix}")

    def get_cache_file_path(self, uri, postfix):
        cache_path = self._uri_to_cache_path(uri, postfix)
        if exists(cache_path):
            return cache_path
        return None

    def exists_in_cache(self, uri, postfix):
        return self.get_cache_file_path(uri, postfix) is not None

    def insert_in_cache(self, uri, postfix, content, mode="w"):
        cache_path = self._uri_to_cache_path(uri, postfix)
        makedirs(dirname(cache_path), exist_ok=True)
        with open(cache_path, mode) as f:
            f.write(content)
        return cache_path

    def get_cache_content(self, uri, postfix, mode="r"):
        if not self.exists_in_cache(uri, postfix):
            return None

        path = self.get_cache_file_path(uri, postfix)
        if not path:
            return None
        with open(path, mode) as f:
            return f.read()
