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


class PersonVehicleAssociation(Base):
    __tablename__ = "person_vehicle_associations"

    association_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    person_entity_id = Column(
        String(30),
        ForeignKey("entities.entity_id"),
        nullable=False
    )

    vehicle_entity_id = Column(
        String(30),
        ForeignKey("entities.entity_id"),
        nullable=False
    )

    camera_id = Column(
        String(30),
        ForeignKey("cameras.camera_id")
    )

    start_time = Column(DateTime)

    end_time = Column(DateTime)

    confidence = Column(Float)

    status = Column(
        String(30),
        default="active"
    )

    extra_data = Column(
    "metadata",
    JSON,
    default=dict
    )