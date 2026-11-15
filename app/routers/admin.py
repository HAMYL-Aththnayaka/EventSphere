
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.database import get_db
from app.models import Venue, Event, TicketCategory, VenueHire, User
from app.agents.agent_system import AgentSystem


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/venue")
def create_venue(
    name: str,
    location: str,
    capacity: int,
    hourly_rate: float,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    if capacity <= 0 or hourly_rate < 0:
        raise HTTPException(400, "Invalid venue details")

    venue = Venue(
        name=name,
        location=location,
        capacity=capacity,
        hourly_rate=hourly_rate,
        description="",
        image="",
        private_hire=True
    )

    db.add(venue)
    db.commit()
    db.refresh(venue)

    return {
        "message": "Venue created",
        "venue_id": venue.id
    }


@router.get("/venues")
def get_venues(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    return db.query(Venue).all()


@router.post("/event")
def create_event(
    title: str,
    category: str,
    venue_id: int,
    start_time: str,
    end_time: str,
    description: str,
    ticket_name: str,
    price: float,
    quantity: int,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    venue = db.get(Venue, venue_id)

    if not venue:
        raise HTTPException(404, "Venue not found")

    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
    except ValueError:
        raise HTTPException(400, "Invalid date/time format")

    if end <= start:
        raise HTTPException(400, "Invalid event time")

    if quantity <= 0 or quantity > venue.capacity or price < 0:
        raise HTTPException(400, "Invalid ticket quantity or price")

    system = AgentSystem(db)

    decision = system.check_venue(
        venue_id,
        start,
        end
    )

    decision_content = decision.get("content", {})

    event = Event(
        title=title,
        category=category,
        venue_id=venue_id,
        start_time=start,
        end_time=end,
        description=description,
        status=(
            "published"
            if decision["performative"] == "AGREE"
            else "draft"
        )
    )

    try:
        db.add(event)
        db.commit()
        db.refresh(event)

        ticket = TicketCategory(
            event_id=event.id,
            name=ticket_name,
            price=price,
            quantity=quantity
        )

        db.add(ticket)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(500, "Could not create event.")

    return {
        "message": "Event created",
        "event_id": event.id,
        "status": event.status,
        "reason": decision_content.get("reason", "Venue decision unavailable.")
    }

@router.get("/events")
def get_events(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    return db.query(Event).all()


@router.post("/event/{event_id}/status")
def update_event_status(
    event_id: int,
    status: str,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    if status not in ["draft", "published", "cancelled"]:
        raise HTTPException(400, "Invalid event status.")

    event = db.get(Event, event_id)

    if not event:
        raise HTTPException(404, "Event not found.")

    if status == "published":
        venue = db.get(Venue, event.venue_id)

        if not venue:
            raise HTTPException(404, "Event venue not found.")

        total_capacity = sum(
            category.quantity
            for category in db.query(TicketCategory).filter(
                TicketCategory.event_id == event.id
            ).all()
        )

        if total_capacity <= 0 or total_capacity > venue.capacity:
            raise HTTPException(
                400,
                "Ticket capacity is invalid or exceeds venue capacity."
            )

        system = AgentSystem(db)
        decision = system.check_venue(
            event.venue_id,
            event.start_time,
            event.end_time
        )

        if decision["performative"] != "AGREE":
            reason = decision.get("content", {}).get(
                "reason", "Venue is unavailable."
            )
            raise HTTPException(409, reason)

    event.status = status
    db.commit()

    return {
        "message": "Event status updated.",
        "event_id": event.id,
        "status": event.status
    }

@router.get("/hires")
def get_hire_requests(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    return db.query(VenueHire).order_by(
        VenueHire.id.desc()
    ).all()


@router.post("/hire/{hire_id}/decision")
def decide_hire_request(
    hire_id: int,
    decision: str,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    if decision not in ["approve", "reject"]:
        raise HTTPException(
            400,
            "Decision must be approve or reject."
        )

    hire = db.get(VenueHire, hire_id)

    if not hire:
        raise HTTPException(404, "Hire request not found.")

    if hire.status != "pending_admin":
        raise HTTPException(
            400,
            "This hire request is not awaiting approval."
        )

    if decision == "reject":
        hire.status = "rejected"
    else:
        system = AgentSystem(db)

        availability = system.check_venue(
            hire.venue_id,
            hire.start_time,
            hire.end_time
        )

        if availability["performative"] != "AGREE":
            reason = availability.get("content", {}).get(
                "reason",
                "Venue is no longer available."
            )
            raise HTTPException(409, reason)

        hire.status = "confirmed"

    db.commit()

    return {
        "message": "Hire request decision saved.",
        "hire_id": hire.id,
        "status": hire.status
    }
