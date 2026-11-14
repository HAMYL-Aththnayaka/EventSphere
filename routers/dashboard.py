from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Event, Booking, Ticket

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def dashboard(db: Session = Depends(get_db)):

    events = db.query(Event).all()

    result = []

    for event in events:

        sold = db.query(
            func.sum(Booking.quantity)
        ).filter(
            Booking.event_id == event.id,
            Booking.status == "confirmed"
        ).scalar() or 0

        revenue = db.query(
            func.sum(Booking.total)
        ).filter(
            Booking.event_id == event.id,
            Booking.status == "confirmed"
        ).scalar() or 0

        checkins = db.query(Ticket).filter(
            Ticket.event_id == event.id,
            Ticket.checked_in == True
        ).count()

        result.append({
            "event": event.title,
            "tickets_sold": sold,
            "revenue": revenue,
            "checkins": checkins
        })

    return result