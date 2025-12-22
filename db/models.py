"""SQLAlchemy models for tracking indexing status."""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Integer, Enum as SQLEnum, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IndexStatus(str, Enum):
    """Status of file indexing."""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class IndexedFile(Base):
    """Track indexing status per file."""
    __tablename__ = "indexed_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String, unique=True, nullable=False, index=True)
    file_hash = Column(String, nullable=False)  # SHA256 of content
    status = Column(SQLEnum(IndexStatus), default=IndexStatus.QUEUED)
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    indexed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
