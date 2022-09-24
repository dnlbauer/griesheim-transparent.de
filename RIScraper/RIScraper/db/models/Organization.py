import uuid

from sqlalchemy import String, Column, Integer
from sqlalchemy.orm import relationship

from db.GUID import GUID
from db.Base import Base
from db.models.Membership import Membership


class Organization(Base):
    __tablename__ = 'organizations'

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(Integer, unique=True)
    name = Column(String, nullable=False)
    memberships = relationship("Membership", backref="organization",
                               primaryjoin=id == Membership.organization_id)
    meetings = relationship("Meeting", back_populates="organization")
