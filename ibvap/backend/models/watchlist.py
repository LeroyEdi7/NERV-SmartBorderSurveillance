from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime
)

from backend.database import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    person_id = Column(
        String(50),
        primary_key=True
    )

    name = Column(
        String(100),
        nullable=False
    )

    embedding = Column(Text)

    status = Column(
        String(30),
        default="active"
    )

    created_at = Column(DateTime)