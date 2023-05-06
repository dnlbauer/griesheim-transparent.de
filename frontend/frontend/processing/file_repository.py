from os.path import join

from django.conf import settings


class FileRepository:

    def __init__(self):
        self.base_path = settings.DOCUMENT_STORE

    def get_file_path(self, uri):
        return join(self.base_path, uri)

    def open_file(self, uri, mode="rb"):
        return open(self.get_file_path(uri), mode)

    def get_file_content(self, uri, mode="rb"):
        return self.open_file(uri, mode).read()
