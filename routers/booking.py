from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Event, TicketCategory
from app.agents.booking_agent import BookingAgent
from app.agents.ticket_agent import TicketAgent

router = APIRouter(prefix="/booking", tags=["Booking"])


@router.post("/create")
def create_booking(
    user_id: int,
    event_id: int,
    category_id: int,
    quantity: int,
    db: Session = Depends(get_db)
):

    event = db.get(Event, event_id)

    if not event or event.status != "published":
        raise HTTPException(400, "Event unavailable")

    agent = BookingAgent(db)

    result = agent.book_ticket(
        user_id,
        event_id,
        category_id,
        quantity
    )

    if result["performative"] == "REFUSE":
        raise HTTPException(400, result["reason"])

    booking = db.get(Booking, result["booking_id"])

    ticket_agent = TicketAgent(db)
    tickets = ticket_agent.create_tickets(booking)

    return {
        "booking": result,
        "tickets": [ticket.code for ticket in tickets]
    }