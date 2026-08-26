from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Float,
    DateTime,
    ForeignKey,
    JSON
)

from backend.database import Base


class CrossCameraTrack(Base):
    __tablename__ = "cross_camera_tracks"

    track_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    entity_id = Column(
        String(30),
        ForeignKey("entities.entity_id"),
        nullable=False
    )

    previous_camera_id = Column(
        String(30),
        ForeignKey("cameras.camera_id")
    )

    current_camera_id = Column(
        String(30),
        ForeignKey("cameras.camera_id")
    )

    previous_timestamp = Column(DateTime)

    current_seen_at = Column(DateTime)

    match_type = Column(String(30))

    confidence = Column(Float)

    extra_data = Column(
    "metadata",
    JSON,
    default=dict
    )

    created_at = Column(DateTime)