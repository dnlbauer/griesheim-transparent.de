import uuid

from sqlalchemy import Column, String, LargeBinary, Integer, DateTime

from db.Base import Base
from db.GUID import GUID


class Document(Base):
    __tablename__ = "documents"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(Integer, unique=True, nullable=False)
    file_name = Column(String, nullable=False)
    content_type = Column(String)
    content_binary = Column(LargeBinary, nullable=False)
    size = Column(Integer, nullable=False)
    author = Column(String)
    creation_date = Column(DateTime)
    last_modified = Column(DateTime)
    last_saved = Column(DateTime)
    content_text = Column(String)
    content_text_ocr = Column(String)

