from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
from app.auth import require_roles
from app.models import User

from app.database import get_db
from app.models import Event, Booking, Ticket, TicketCategory, Venue, AgentMessage

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def dashboard(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):

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

        venue = db.get(Venue, event.venue_id)
        categories = db.query(TicketCategory).filter(
            TicketCategory.event_id == event.id
        ).all()
        ticket_capacity = sum(category.quantity for category in categories)
        result.append({
            "event": event.title,
            "title": event.title,
            "tickets_sold": sold,
            "revenue": revenue,
            "checkins": checkins,
            "capacity": ticket_capacity + sold,
            "venue_capacity": venue.capacity if venue else 0,
            "remaining_capacity": ticket_capacity
        })

    messages = db.query(AgentMessage).order_by(
        AgentMessage.id.desc()
    ).limit(100).all()

    return {
        "events": result,
        "agent_logs": [
            {
                "conversation_id": message.conversation_id,
                "sender": message.sender,
                "receiver": message.receiver,
                "performative": message.performative,
                "content": json.loads(message.content),
                "created_at": message.created_at.isoformat()
            }
            for message in reversed(messages)
        ]
    }