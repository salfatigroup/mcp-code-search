"""SQLAlchemy models for tracking indexing status and code intelligence."""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, DateTime, Integer, Enum as SQLEnum, Text, Boolean
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


class FileSummary(Base):
    """Store AI-generated file summaries for semantic search."""
    __tablename__ = "file_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String, unique=True, nullable=False, index=True)
    summary = Column(Text, nullable=False)
    file_hash = Column(String, nullable=False)
    language = Column(String, nullable=True)
    loc = Column(Integer, default=0)  # Lines of code
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Symbol(Base):
    """Code symbols (functions, classes, methods, variables)."""
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String, nullable=False, index=True)
    symbol_name = Column(String, nullable=False, index=True)
    symbol_type = Column(String, nullable=False, index=True)  # function, class, method, variable
    line_start = Column(Integer, nullable=False)
    line_end = Column(Integer, nullable=False)
    parent_symbol = Column(String, nullable=True)  # For methods: parent class
    signature = Column(Text, nullable=True)
    docstring = Column(Text, nullable=True)
    is_exported = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CodeRelationship(Base):
    """Code relationships (calls, imports, inheritance)."""
    __tablename__ = "code_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String, nullable=False, index=True)
    source_symbol = Column(String, nullable=False, index=True)
    source_line = Column(Integer, nullable=False)
    target_file = Column(String, nullable=True)
    target_symbol = Column(String, nullable=False, index=True)
    relationship_type = Column(String, nullable=False, index=True)  # calls, imports, inherits
    is_external = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
