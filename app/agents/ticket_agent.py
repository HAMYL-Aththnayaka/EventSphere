
from datetime import datetime
import secrets

from sqlalchemy import update

from app.models import Ticket, Booking, Event


class TicketAgent:
    def __init__(self, db):
        self.db = db

    def create_tickets(self, booking):
        tickets = []

        try:
            for _ in range(booking.quantity):
                ticket = Ticket(
                    booking_id=booking.id,
                    event_id=booking.event_id,
                    code=secrets.token_urlsafe(32),
                    status="valid"
                )

                self.db.add(ticket)
                tickets.append(ticket)

            self.db.commit()

            for ticket in tickets:
                self.db.refresh(ticket)

            return tickets

        except Exception:
            self.db.rollback()
            raise

    def scan_ticket(self, code, event_id):
        ticket = self.db.query(Ticket).filter(
            Ticket.code == code
        ).first()

        if not ticket:
            return {
                "result": "REJECTED",
                "reason": "Invalid ticket"
            }

        booking = self.db.get(Booking, ticket.booking_id)
        event = self.db.get(Event, ticket.event_id)

        if not booking or booking.status != "confirmed":
            return {
                "result": "REJECTED",
                "reason": "Cancelled or invalid booking"
            }

        if ticket.status != "valid" or ticket.checked_in:
            return {
                "result": "REJECTED",
                "reason": "Ticket already used or cancelled"
            }

        if ticket.event_id != event_id:
            return {
                "result": "REJECTED",
                "reason": "Wrong event"
            }

        if not event:
            return {
                "result": "REJECTED",
                "reason": "Event not found"
            }

        now = datetime.utcnow()

        if now < event.start_time:
            return {
                "result": "REJECTED",
                "reason": "Event has not started yet"
            }

        if now > event.end_time:
            return {
                "result": "REJECTED",
                "reason": "Event has ended"
            }

        result = self.db.execute(
            update(Ticket)
            .where(
                Ticket.id == ticket.id,
                Ticket.checked_in == False,
                Ticket.status == "valid"
            )
            .values(
                checked_in=True,
                status="used"
            )
        )

        if result.rowcount == 0:
            self.db.rollback()
            return {
                "result": "REJECTED",
                "reason": "Ticket already used"
            }

        self.db.commit()

        return {
            "result": "ADMITTED",
            "reason": "Valid ticket"
        }

    def cancel_booking_tickets(self, booking_id):
        try:
            self.db.execute(
                update(Ticket)
                .where(
                    Ticket.booking_id == booking_id,
                    Ticket.status != "cancelled"
                )
                .values(
                    checked_in=False,
                    status="cancelled"
                )
            )
            self.db.commit()
            return {
                "performative": "INFORM",
                "content": {"booking_id": booking_id, "status": "cancelled"}
            }
        except Exception:
            self.db.rollback()
            raise

    def handle_message(self, agent_message):
        if agent_message["performative"] != "REQUEST":
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "TicketAgent requires REQUEST messages."
                }
            }

        content = agent_message["content"]
        action = content.get("action")

        if action == "CREATE_TICKETS":
            booking_id = content.get("booking_id")

            booking = self.db.get(Booking, booking_id)

            if not booking or booking.status != "confirmed":
                return {
                    "performative": "REFUSE",
                    "content": {
                        "reason": "Confirmed booking not found."
                    }
                }

            tickets = self.create_tickets(booking)

            return {
                "performative": "AGREE",
                "content": {
                    "booking_id": booking.id,
                    "tickets": [
                        {
                            "ticket_id": ticket.id,
                            "code": ticket.code
                        }
                        for ticket in tickets
                    ]
                }
            }

        if action == "SCAN_TICKET":
            result = self.scan_ticket(
                content.get("code"),
                content.get("event_id")
            )

            return {
                "performative": (
                    "AGREE"
                    if result["result"] == "ADMITTED"
                    else "REFUSE"
                ),
                "content": result
            }

        if action == "CANCEL_BOOKING_TICKETS":
            booking_id = content.get("booking_id")
            if not booking_id:
                return {
                    "performative": "REFUSE",
                    "content": {"reason": "Booking ID is required."}
                }
            return self.cancel_booking_tickets(booking_id)

        return {
            "performative": "REFUSE",
            "content": {
                "reason": "Unknown TicketAgent action."
            }
        }
