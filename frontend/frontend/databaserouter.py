import inspect

class DatabaseRouter:
    """
    Routes risdb models to RIS database and everthing else to the default
    database
    """

    DEFAULT_DB = "default"
    RIS_DB = "ris"

    def _is_risdb_model(self, model):
        mod = inspect.getmodule(model)
        _base, _sep, stem = mod.__name__.partition('.')
        return stem.endswith("risdb")

    def _route(self, model):
        if self._is_risdb_model(model):
            return self.RIS_DB
        return self.DEFAULT_DB

    def db_for_read(self, model):
        return self._route(model)

    def db_for_write(self, model):
        return self._route(model)

    def allow_relation(self, obj1, obj2):
        # allow relations between objects in the same database
        return self._is_risdb_model(obj1) == self._is_risdb_model(obj2)

    def allow_migrate(self, db, app_label, model_name=None):
        # no migrations in risdb. db is handled by the scraper
        return db != self.RIS_DB
