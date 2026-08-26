from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    DateTime,
    ForeignKey
)

from backend.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    alert_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    event_id = Column(
        String(50),
        ForeignKey("events.event_id"),
        nullable=False
    )

    title = Column(
        String(200),
        nullable=False
    )

    message = Column(Text)

    severity = Column(
        String(20),
        nullable=False
    )

    status = Column(
        String(30),
        default="ACTIVE"
    )

    created_at = Column(
        DateTime
    )

    acknowledged_at = Column(
        DateTime
    )

    resolved_at = Column(
        DateTime
    )