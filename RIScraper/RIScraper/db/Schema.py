from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .Base import Base
from .TransactionManager import TransactionManager


class Schema:
    def __init__(self, uri, verbose=False):
        self.engine = create_engine(uri, echo=verbose, future=True)
        metadata = Base.metadata
        metadata.create_all(self.engine, checkfirst=True)

    def create_transaction(self):
        return TransactionManager(self)

    def create_session(self):
        return Session(self.engine)
