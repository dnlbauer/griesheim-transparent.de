from sqlalchemy import Column, String, UniqueConstraint
import uuid

from sqlalchemy.orm import relationship

from db.Base import Base
from db.GUID import GUID
from db.models.Membership import Membership


class Person(Base):
    __tablename__ = "persons"
    __table_args__ = (
        UniqueConstraint("first_name", "last_name"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    memberships = relationship("Membership", backref="person",
                               primaryjoin=id == Membership.person_id)
