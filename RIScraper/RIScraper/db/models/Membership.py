import uuid

from sqlalchemy import Column, ForeignKey, UniqueConstraint

from db.Base import Base
from db.GUID import GUID


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("person_id", "organization_id"),
    )

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id = Column(GUID(), ForeignKey("persons.id"),
                       primary_key=True, nullable=False)
    organization_id = Column(GUID(), ForeignKey("organizations.id"),
                             primary_key=True, nullable=False)
