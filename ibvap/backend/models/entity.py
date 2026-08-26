from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func

from backend.database import Base


class Entity(Base):
    __tablename__ = "entities"

    entity_id = Column(
        String(30),
        primary_key=True
    )

    entity_type = Column(
        String(30),
        nullable=False
    )

    first_seen = Column(
        DateTime,
        server_default=func.now()
    )

    last_seen = Column(
        DateTime,
        server_default=func.now()
    )

    status = Column(
        String(30),
        default="active"
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )