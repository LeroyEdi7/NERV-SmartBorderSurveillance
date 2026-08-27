from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.event import Event
from backend.models.camera import Camera
from backend.models.entity import Entity
from backend.models.zone import Zone
from backend.schemas.event import EventCreate, EventResponse

from backend.websocket_manager import manager


router = APIRouter(
    prefix="/api/v1/events",
    tags=["Events"]
)


# ============================================================
# POST /api/v1/events
# ============================================================

@router.post(
    "",
    response_model=EventResponse,
    status_code=201
)
async def create_event(
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

    except Exception:
        db.rollback()
        raise


    await manager.broadcast({
        "type": "NEW_EVENT",
        "event": {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "camera_id": event.camera_id,
            "entity_id": event.entity_id,
            "severity": event.severity,
            "confidence": event.confidence,
            "zone_id": event.zone_id,
            "timestamp": event.timestamp.isoformat(),
            "status": event.status,
            "snapshot_path": event.snapshot_path,
            "metadata": event.extra_data
        }
    })

    return event


# ============================================================
# GET /api/v1/events
# ============================================================

@router.get(
    "",
    response_model=list[EventResponse]
)
def get_events(
    camera_id: Optional[str] = Query(
        default=None,
        description="Filter events by camera ID"
    ),

    event_type: Optional[str] = Query(
        default=None,
        description="Filter events by event type"
    ),

    severity: Optional[str] = Query(
        default=None,
        description="Filter events by severity"
    ),

    status: Optional[str] = Query(
        default=None,
        description="Filter events by status"
    ),

    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of events to return"
    ),

    offset: int = Query(
        default=0,
        ge=0,
        description="Number of events to skip"
    ),

    db: Session = Depends(get_db)
):
    """
    Retrieve surveillance events.

    Events are returned newest first.
    """

    query = db.query(Event)

    # --------------------------------------------------------
    # Filters
    # --------------------------------------------------------

    if camera_id:
        query = query.filter(
            Event.camera_id == camera_id
        )

    if event_type:
        query = query.filter(
            Event.event_type == event_type
        )

    if severity:
        query = query.filter(
            Event.severity == severity
        )

    if status:
        query = query.filter(
            Event.status == status
        )

    # --------------------------------------------------------
    # Sort newest events first
    # --------------------------------------------------------

    query = query.order_by(
        Event.timestamp.desc()
    )

    # --------------------------------------------------------
    # Pagination
    # --------------------------------------------------------

    events = (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )

    return events