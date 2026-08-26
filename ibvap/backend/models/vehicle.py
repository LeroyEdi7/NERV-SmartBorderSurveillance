from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey
)

from backend.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    vehicle_id = Column(
        String(30),
        primary_key=True
    )

    entity_id = Column(
        String(30),
        ForeignKey("entities.entity_id"),
        nullable=True
    )

    plate_number = Column(String(30))

    vehicle_type = Column(String(50))

    color = Column(String(30))

    first_seen = Column(DateTime)

    last_seen = Column(DateTime)

    created_at = Column(DateTime)