"""Base model class for all database models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    Uses SQLAlchemy 2.0 declarative style with mapped_column and Mapped type hints.
    """

    pass
