from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Venue, Event, TicketCategory

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/venue")
def create_venue(
    name: str,
    location: str,
    capacity: int,
    hourly_rate: float,
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

    return {"message": "Venue created"}


@router.get("/venues")
def get_venues(db: Session = Depends(get_db)):
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
    db: Session = Depends(get_db)
):

    from datetime import datetime
    from app.agents.venue_agent import VenueAgent

    venue = db.get(Venue, venue_id)

    if not venue:
        raise HTTPException(404, "Venue not found")

    start = datetime.fromisoformat(start_time)
    end = datetime.fromisoformat(end_time)

    if end <= start:
        raise HTTPException(400, "Invalid event time")

    if quantity <= 0 or quantity > venue.capacity or price < 0:
        raise HTTPException(400, "Invalid ticket quantity or price")

    agent = VenueAgent(db)
    decision = agent.check_venue(venue_id, start, end)

    event = Event(
        title=title,
        category=category,
        venue_id=venue_id,
        start_time=start,
        end_time=end,
        description=description,
        status="published"
    )

    if decision["performative"] == "REFUSE":
        event.status = "draft"

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

    return {
        "message": "Event created",
        "status": event.status,
        "reason": decision["reason"]
    }