import sys, inspect

class DatabaseRouter:
    def _is_risdb_model(self, model):
        if model._meta.app_label != "frontend":
            return False

        mod = inspect.getmodule(model)
        base, _sep, _stem = mod.__name__.partition('.')
        return _stem.startswith("risdb")

    def db_for_read(self, model, **hints):
        if self._is_risdb_model(model):
            return "ris"
        return "default"

    def db_for_write(self, model, **hints):
        if self._is_risdb_model(model):
            return "ris"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db != "ris"
