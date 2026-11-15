from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_roles
from app.models import Booking, Event, Ticket, User
from app.agents.agent_system import AgentSystem
from app.qr import generate_qr

router = APIRouter(prefix="/booking", tags=["Booking"])


@router.post("/create")
def create_booking(
    event_id: int,
    category_id: int,
    quantity: int,
    current_user: User = Depends(require_roles("attendee")),
    db: Session = Depends(get_db)
):
    if quantity <= 0 or quantity > 6:
        raise HTTPException(
            status_code=400,
            detail="You can book between 1 and 6 tickets."
        )

    event = db.get(Event, event_id)

    if not event or event.status != "published":
        raise HTTPException(
            status_code=400,
            detail="Event unavailable."
        )

    agent_system = AgentSystem(db)

    result = agent_system.book_tickets(
        user_id=current_user.id,
        event_id=event_id,
        category_id=category_id,
        quantity=quantity
    )

    if result["performative"] != "AGREE":
        reason = result.get("content", {}).get(
            "reason",
            "Booking could not be completed."
        )
        raise HTTPException(
            status_code=(
                500
                if result["performative"] == "FAILURE"
                else 400
            ),
            detail=reason
        )

    ticket_details = []

    for ticket in result["content"]["tickets"]:
        qr_url = generate_qr(ticket["code"])

        ticket_details.append({
            "ticket_id": ticket["ticket_id"],
            "ticket_code": ticket["code"],
            "qr_code": qr_url
        })

    return {
        "message": "Booking successful.",
        "booking": result["content"]["booking"],
        "tickets": ticket_details
    }



@router.get("/history")
def booking_history(
    current_user: User = Depends(require_roles("attendee")),
    db: Session = Depends(get_db)
):
    bookings = db.query(Booking).filter(
        Booking.user_id == current_user.id
    ).order_by(Booking.id.desc()).all()

    history = []

    for booking in bookings:
        event = db.get(Event, booking.event_id)

        tickets = db.query(Ticket).filter(
            Ticket.booking_id == booking.id
        ).all()

        history.append({
            "booking_id": booking.id,
            "event_id": booking.event_id,
            "event_title": event.title if event else "Event unavailable",
            "quantity": booking.quantity,
            "total": booking.total,
            "refund_amount": booking.refund_amount,
            "payment_reference": booking.payment_reference,
            "status": booking.status,
            "tickets": [
            {
                    "ticket_id": ticket.id,
                    "ticket_code": ticket.code,
                    "qr_code": generate_qr(ticket.code),
                    "status": ticket.status,
                    "checked_in": ticket.checked_in
                }
                for ticket in tickets
            ]
        })

    return {
        "bookings": history,
        "total_bookings": len(history)
    }

@router.post("/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(require_roles("attendee")),
    db: Session = Depends(get_db)
):
    agent_system = AgentSystem(db)

    result = agent_system.cancel_booking(
        booking_id=booking_id,
        user_id=current_user.id
    )

    if result["performative"] != "INFORM":
        content = result.get("content", {})
        raise HTTPException(
            status_code=400,
            detail=content.get("reason", "Booking cancellation failed.")
        )

    return {
        "message": "Booking cancellation processed.",
        **result["content"]
    }