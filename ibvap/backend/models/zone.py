from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    JSON
)

from backend.database import Base


class Zone(Base):
    __tablename__ = "zones"

    zone_id = Column(
        String(30),
        primary_key=True
    )

    name = Column(
        String(100),
        nullable=False
    )

    zone_type = Column(
        String(30),
        nullable=False
    )

    camera_id = Column(
        String(30),
        ForeignKey("cameras.camera_id")
    )

    polygon = Column(
        JSON,
        nullable=False
    )

    severity = Column(
        String(20),
        default="HIGH"
    )

    enabled = Column(
        Boolean,
        default=True
    )

    created_at = Column(DateTime)