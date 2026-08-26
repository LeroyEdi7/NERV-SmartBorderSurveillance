from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.database import get_db
from backend.models.event import Event
from backend.models.camera import Camera
from backend.models.entity import Entity
from backend.models.zone import Zone
from backend.schemas.event import EventCreate, EventResponse


router = APIRouter(
    prefix="/api/v1/events",
    tags=["Events"]
)


@router.post(
    "",
    response_model=EventResponse,
    status_code=201
)
def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new surveillance event.
    """

    # Check if event already exists
    existing_event = (
        db.query(Event)
        .filter(Event.event_id == event_data.event_id)
        .first()
    )

    if existing_event:
        raise HTTPException(
            status_code=409,
            detail="Event with this event_id already exists"
        )

    # Validate camera
    if event_data.camera_id:
        camera = (
            db.query(Camera)
            .filter(Camera.camera_id == event_data.camera_id)
            .first()
        )

        if not camera:
            raise HTTPException(
                status_code=404,
                detail=f"Camera '{event_data.camera_id}' not found"
            )

    # Validate entity
    if event_data.entity_id:
        entity = (
            db.query(Entity)
            .filter(Entity.entity_id == event_data.entity_id)
            .first()
        )

        if not entity:
            raise HTTPException(
                status_code=404,
                detail=f"Entity '{event_data.entity_id}' not found"
            )

    # Validate zone
    if event_data.zone_id:
        zone = (
            db.query(Zone)
            .filter(Zone.zone_id == event_data.zone_id)
            .first()
        )

        if not zone:
            raise HTTPException(
                status_code=404,
                detail=f"Zone '{event_data.zone_id}' not found"
            )

    # Create database object
    event = Event(
        event_id=event_data.event_id,
        event_type=event_data.event_type,
        camera_id=event_data.camera_id,
        entity_id=event_data.entity_id,
        severity=event_data.severity,
        confidence=event_data.confidence,
        zone_id=event_data.zone_id,
        timestamp=event_data.timestamp,
        status="NEW",
        snapshot_path=event_data.snapshot_path,
        extra_data=event_data.metadata or {}
    )

    # Save to PostgreSQL
    db.add(event)

    try:
        db.commit()
        db.refresh(event)

    except IntegrityError as e:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Event violates a database constraint."
        )

    return event