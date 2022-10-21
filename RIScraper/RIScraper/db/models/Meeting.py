import uuid

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship

from db.Base import Base
from db.GUID import GUID

association_document_meeting = Table(
    "document_meeting",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("meeting_id", ForeignKey("meetings.id"), primary_key=True),
)

association_document_agenda_item = Table(
    "document_agenda_item",
    Base.metadata,
    Column("document_id", ForeignKey("documents.id"), primary_key=True),
    Column("agenda_item_id", ForeignKey("agendaitems.id"), primary_key=True),
)

association_consultation_meeting = Table(
    "consultation_meeting",
    Base.metadata,
    Column("consultation_id", ForeignKey("consultations.id"), primary_key=True),
    Column("meeting_id", ForeignKey("meetings.id"), primary_key=True),
)


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id = Column(Integer, nullable=False, unique=True)
    title = Column(String, nullable=False)
    title_short = Column(String)
    date = Column(DateTime)
    organization_id = Column(GUID(), ForeignKey("organizations.id"))
    organization = relationship("Organization", back_populates="meetings")
    agendaItems = relationship("AgendaItem", back_populates="meeting")
    documents = relationship("Document",
                             secondary=association_document_meeting,
                             backref="meetings")
    consultations = relationship("Consultation", secondary=association_consultation_meeting, backref="meetings")


class AgendaItem(Base):
    __tablename__ = "agendaitems"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    agenda_item_id = Column(Integer, nullable=False, unique=True)
    title = Column(String, nullable=False)
    decision = Column(String)
    vote = Column(String)
    text = Column(String)
    meeting_id = Column(GUID(), ForeignKey("meetings.id"))
    meeting = relationship("Meeting", back_populates="agendaItems")
    consultation_id = Column(GUID(), ForeignKey("consultations.id"))
    consultation = relationship("Consultation", back_populates="agendaItems")
    documents = relationship("Document",
                             secondary=association_document_agenda_item,
                             backref="agendaItems")
