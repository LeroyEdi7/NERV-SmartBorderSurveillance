from datetime import datetime
from typing import Any, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    event_id: str = Field(
        ...,
        max_length=50,
        description="Unique event identifier"
    )

    event_type: str = Field(
        ...,
        max_length=50,
        description="Type of security event"
    )

    camera_id: Optional[str] = Field(
        default=None,
        max_length=30
    )

    entity_id: Optional[str] = Field(
        default=None,
        max_length=30
    )

    severity: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    ] = "LOW"

    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0
    )

    zone_id: Optional[str] = Field(
        default=None,
        max_length=30
    )

    timestamp: datetime

    snapshot_path: Optional[str] = None

    metadata: Optional[dict[str, Any]] = None


class EventResponse(BaseModel):

    event_id: str
    event_type: str
    camera_id: Optional[str]
    entity_id: Optional[str]
    severity: str
    confidence: Optional[float]
    zone_id: Optional[str]
    timestamp: datetime
    status: str
    snapshot_path: Optional[str]

    # API field "metadata" comes from SQLAlchemy attribute "extra_data"
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        validation_alias="extra_data",
        serialization_alias="metadata"
    )

    model_config = ConfigDict(
        from_attributes=True
    )