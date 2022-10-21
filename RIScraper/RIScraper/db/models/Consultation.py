import uuid

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.testing.schema import Table

from db.Base import Base
from db.GUID import GUID

association_document_consultation = Table(
    "document_consultation",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("consultation_id", ForeignKey("consultations.id"), primary_key=True),
)

class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    consultation_id = Column(Integer, nullable=False, unique=True)
    name = Column(String, nullable=False, unique=True)
    topic = Column(String, nullable=False)
    type = Column(String)
    text = Column(String)
    documents = relationship("Document",
                             secondary=association_document_consultation,
                             backref="consultations")
    agendaItems = relationship("AgendaItem", back_populates="consultation")
