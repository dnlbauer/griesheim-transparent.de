import inspect
from typing import Any

from django.db import models


class DatabaseRouter:
    """
    Routes models app to scraped database and everything else to the default
    database
    """

    DEFAULT_DB = "default"
    SCRAPED_DB = "scraped"

    def _is_scraped_data_model(self, model: type[models.Model]) -> bool:
        module = inspect.getmodule(model)
        if not module:
            return False
        base, _sep, _stem = module.__name__.partition(".")
        return base == "models"

    def _route(self, model: type[models.Model]) -> str:
        if self._is_scraped_data_model(model):
            return self.SCRAPED_DB
        return self.DEFAULT_DB

    def db_for_read(self, model: type[models.Model], **hints: Any) -> str:
        return self._route(model)

    def db_for_write(self, model: type[models.Model], **hints: Any) -> str:
        return self._route(model)

    def allow_relation(
        self, obj1: models.Model, obj2: models.Model, **hints: Any
    ) -> bool:
        # allow relations between objects in the same database
        return self._is_scraped_data_model(type(obj1)) == self._is_scraped_data_model(
            type(obj2)
        )

    def allow_migrate(
        self, db: str, app_label: str, model_name: str | None = None, **hints: Any
    ) -> bool:
        if app_label == "models":
            return db == self.SCRAPED_DB
        return db == self.DEFAULT_DB
