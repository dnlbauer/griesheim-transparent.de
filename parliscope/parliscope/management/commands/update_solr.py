from typing import Any

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from parliscope.tasks.indexing import update_solr_index


class Command(BaseCommand):
    help = "Update solr index from ris database"

    DEFAULT_CHUNK_SIZE = 10  # chunk size for solr document commit

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--chunk_size",
            help=f"chunk size for sending documents to solr (default: {self.DEFAULT_CHUNK_SIZE})",
            type=int,
            default=self.DEFAULT_CHUNK_SIZE,
        )
        parser.add_argument(
            "--force", help="force update for all documents", action="store_true"
        )
        parser.add_argument(
            "--no-ocr",
            help="allow ocr for documents (takes a long time)",
            action="store_false",
        )

    def handle(self, **options: Any) -> None:
        force = options["force"]
        allow_ocr = options["no_ocr"]
        chunk_size = options.get("chunk_size", self.DEFAULT_CHUNK_SIZE)

        update_solr_index(
            force=force,
            allow_ocr=allow_ocr,
            chunk_size=chunk_size,
        )
