from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text
)

from sqlalchemy.dialects.postgresql import JSONB

from backend.database import Base


class Event(Base):
    __tablename__ = "events"

    event_id = Column(
        String(50),
        primary_key=True
    )

    event_type = Column(
        String(50),
        nullable=False
    )

    camera_id = Column(
        String(30),
        ForeignKey("cameras.camera_id")
    )

    entity_id = Column(
        String(30),
        ForeignKey("entities.entity_id")
    )

    severity = Column(
        String(20),
        nullable=False,
        default="LOW"
    )

    confidence = Column(Float)

    zone_id = Column(
        String(30),
        ForeignKey("zones.zone_id")
    )

    timestamp = Column(
        DateTime,
        nullable=False
    )

    status = Column(
        String(30),
        default="NEW"
    )

    snapshot_path = Column(Text)

    extra_data = Column(
        "metadata",
        JSONB,
        default=dict
    )