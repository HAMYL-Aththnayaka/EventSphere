
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Event, Venue, TicketCategory

router = APIRouter(prefix="/events", tags=["Public Events"])


@router.get("")
def discover_events(
    search: str = "",
    category: str = "",
    db: Session = Depends(get_db)
):
    query = db.query(Event).filter(
        Event.status == "published"
    )

    if search.strip():
        query = query.filter(
            Event.title.ilike(f"%{search.strip()}%")
        )

    if category.strip():
        query = query.filter(
            Event.category.ilike(f"%{category.strip()}%")
        )

    events = query.order_by(Event.start_time.asc()).all()

    results = []

    for event in events:
        venue = db.get(Venue, event.venue_id)

        categories = db.query(TicketCategory).filter(
            TicketCategory.event_id == event.id
        ).all()

        results.append({
            "id": event.id,
            "title": event.title,
            "category": event.category,
            "description": event.description,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat(),
            "venue": {
                "id": venue.id,
                "name": venue.name,
                "location": venue.location
            } if venue else None,
            "ticket_categories": [
                {
                    "id": item.id,
                    "name": item.name,
                    "price": item.price,
                    "available": item.quantity
                }
                for item in categories
            ]
        })

    return {
        "events": results,
        "total": len(results)
    }


@router.get("/{event_id}")
def event_details(
    event_id: int,
    db: Session = Depends(get_db)
):
    event = db.get(Event, event_id)

    if not event or event.status != "published":
        raise HTTPException(
            status_code=404,
            detail="Published event not found."
        )

    venue = db.get(Venue, event.venue_id)

    categories = db.query(TicketCategory).filter(
        TicketCategory.event_id == event.id
    ).all()

    return {
        "id": event.id,
        "title": event.title,
        "category": event.category,
        "description": event.description,
        "start_time": event.start_time.isoformat(),
        "end_time": event.end_time.isoformat(),
        "venue": {
            "id": venue.id,
            "name": venue.name,
            "location": venue.location,
            "capacity": venue.capacity
        } if venue else None,
        "ticket_categories": [
            {
                "id": item.id,
                "name": item.name,
                "price": item.price,
                "available": item.quantity
            }
            for item in categories
        ]
    }
