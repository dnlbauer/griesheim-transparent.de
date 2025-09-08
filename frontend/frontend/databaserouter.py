import inspect


class DatabaseRouter:
    """
    Routes risdb models to RIS database and everthing else to the default
    database
    """

    DEFAULT_DB = "default"
    RIS_DB = "ris"

    def _is_risdb_model(self, model):
        module = inspect.getmodule(model)
        if not module:
            return False
        base, _sep, _stem = module.__name__.partition('.')
        return base == "ris"

    def _route(self, model):
        if self._is_risdb_model(model):
            return self.RIS_DB
        return self.DEFAULT_DB

    def db_for_read(self, model, **hints):
        return self._route(model)

    def db_for_write(self, model, **hints):
        return self._route(model)

    def allow_relation(self, obj1, obj2, **hints):
        # allow relations between objects in the same database
        return self._is_risdb_model(obj1) == self._is_risdb_model(obj2)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == "ris":
            return db == "ris"
        return db == "default"

