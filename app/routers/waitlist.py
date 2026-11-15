
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.auth import require_roles
from app.database import get_db
from app.models import User, Event, Booking, Ticket, Venue, TicketCategory, AgentMessage

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

        capacity = venue.capacity if venue else 0

        result.append({
            "event_id": event.id,
            "event": event.title,
            "status": event.status,
            "tickets_sold": sold,
            "revenue": round(float(revenue), 2),
            "checkins": checkins,
            "venue_capacity": capacity,
            "remaining_capacity": max(0, capacity - sold)
        })

    messages = db.query(AgentMessage).order_by(
        AgentMessage.id.desc()
    ).limit(50).all()

    agent_logs = []

    for message in messages:
        try:
            content = json.loads(message.content)
        except (ValueError, TypeError):
            content = message.content

        agent_logs.append({
            "conversation_id": message.conversation_id,
            "sender": message.sender,
            "receiver": message.receiver,
            "performative": message.performative,
            "content": content,
            "created_at": message.created_at.isoformat()
        })

    return {
        "events": result,
        "agent_logs": agent_logs
    }
