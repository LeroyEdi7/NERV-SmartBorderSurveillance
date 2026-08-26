from sqlalchemy import Column, String, Float, Text, DateTime
from sqlalchemy.sql import func

from backend.database import Base


class Camera(Base):
    __tablename__ = "cameras"

    camera_id = Column(String(30), primary_key=True)

    name = Column(String(100), nullable=False)

    location = Column(String(150))

    latitude = Column(Float)

    longitude = Column(Float)

    stream_url = Column(Text)

    status = Column(String(20), default="offline")

    created_at = Column(
        DateTime,
        server_default=func.now()
    )

    updated_at = Column(
        DateTime,
        server_default=func.now()
    )