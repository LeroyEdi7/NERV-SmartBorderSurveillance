from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    JSON
)

from backend.database import Base


class Detection(Base):
    __tablename__ = "detections"

    detection_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    camera_id = Column(
        String(30),
        ForeignKey("cameras.camera_id"),
        nullable=False
    )

    entity_id = Column(
        String(30),
        ForeignKey("entities.entity_id"),
        nullable=True
    )

    object_type = Column(
        String(50),
        nullable=False
    )

    confidence = Column(Float)

    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)
    bbox_x2 = Column(Float)
    bbox_y2 = Column(Float)

    track_id = Column(Integer)

    frame_id = Column(BigInteger)

    timestamp = Column(
        DateTime,
        nullable=False
    )

    extra_data = Column(
    "metadata",
    JSON,
    default=dict
    )