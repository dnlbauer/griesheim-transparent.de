import logging


class TransactionManager:

    def __init__(self, schema):
        self.schema = schema
        self.session = schema.create_session()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is not None:
            logging.error(f"Transaction failed: {exc_type}, {exc_value}")
            logging.error(exc_traceback)
            self.session.rollback()
        else:
            self.session.commit()
