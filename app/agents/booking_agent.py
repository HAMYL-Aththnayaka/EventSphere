
import uuid
from datetime import datetime, timedelta

from sqlalchemy import update

from app.models import (
    Booking,
    Ticket,
    TicketCategory,
    Event,
    Waitlist
)


class BookingAgent:
    def __init__(self, db):
        self.db = db

    def book_ticket(self, user_id, event_id, category_id, quantity):
        if quantity < 1 or quantity > 6:
            return {
                "performative": "REFUSE",
                "reason": "Maximum 6 tickets per booking."
            }

        category = self.db.query(TicketCategory).filter(
            TicketCategory.id == category_id,
            TicketCategory.event_id == event_id
        ).first()

        if not category:
            return {
                "performative": "REFUSE",
                "reason": "Invalid ticket category."
            }

        try:
            result = self.db.execute(
                update(TicketCategory)
                .where(
                    TicketCategory.id == category_id,
                    TicketCategory.quantity >= quantity
                )
                .values(
                    quantity=TicketCategory.quantity - quantity
                )
            )

            if result.rowcount == 0:
                self.db.rollback()
                return {
                    "performative": "REFUSE",
                    "reason": "Not enough tickets available."
                }

            total = category.price * quantity

            booking = Booking(
                user_id=user_id,
                event_id=event_id,
                category_id=category_id,
                quantity=quantity,
                total=total,
                payment_reference="SIM-" + uuid.uuid4().hex[:10],
                status="confirmed"
            )

            self.db.add(booking)
            self.db.commit()
            self.db.refresh(booking)

            return {
                "performative": "AGREE",
                "booking_id": booking.id,
                "total": total,
                "payment_reference": booking.payment_reference
            }

        except Exception:
            self.db.rollback()
            raise

    def book_waitlist_offer(self, waitlist_id, user_id):
        entry = self.db.query(Waitlist).filter(
            Waitlist.id == waitlist_id,
            Waitlist.user_id == user_id
        ).first()

        if not entry or entry.status != "offered":
            return {
                "performative": "REFUSE",
                "content": {"reason": "This waitlist offer is no longer active."}
            }

        if not entry.hold_until or entry.hold_until <= datetime.utcnow():
            return {
                "performative": "REFUSE",
                "content": {"reason": "This waitlist offer has expired."}
            }

        event = self.db.get(Event, entry.event_id)
        category = self.db.get(TicketCategory, entry.category_id)

        if not event or event.status != "published" or not category:
            return {
                "performative": "REFUSE",
                "content": {"reason": "The event or ticket category is unavailable."}
            }

        try:
            # The seat was already reserved when the offer was created.
            # Change the offer status atomically; do not decrement inventory again.
            result = self.db.execute(
                update(Waitlist)
                .where(
                    Waitlist.id == waitlist_id,
                    Waitlist.user_id == user_id,
                    Waitlist.status == "offered",
                    Waitlist.hold_until > datetime.utcnow()
                )
                .values(status="accepted")
            )

            if result.rowcount == 0:
                self.db.rollback()
                return {
                    "performative": "REFUSE",
                    "content": {"reason": "This offer has expired or was already used."}
                }

            booking = Booking(
                user_id=user_id,
                event_id=entry.event_id,
                category_id=entry.category_id,
                quantity=1,
                total=category.price,
                payment_reference="SIM-" + uuid.uuid4().hex[:10],
                status="confirmed"
            )

            self.db.add(booking)
            self.db.commit()
            self.db.refresh(booking)

            return {
                "performative": "AGREE",
                "content": {
                    "booking_id": booking.id,
                    "total": booking.total,
                    "payment_reference": booking.payment_reference
                }
            }

        except Exception:
            self.db.rollback()
            raise

    def cancel_booking(self, booking_id, user_id):
        booking = self.db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.user_id == user_id
        ).first()

        if not booking:
            return {
                "performative": "REFUSE",
                "content": {"reason": "Booking not found."}
            }

        if booking.status != "confirmed":
            return {
                "performative": "REFUSE",
                "content": {"reason": "This booking is not active."}
            }

        event = self.db.get(Event, booking.event_id)

        if not event:
            return {
                "performative": "REFUSE",
                "content": {"reason": "Event not found."}
            }

        try:
            booking.status = "cancelled"

            # Refund eligibility and seat availability are separate rules.
            if event.start_time > datetime.utcnow() + timedelta(hours=24):
                refund = booking.total
            else:
                refund = 0

            # Always release the seats when a confirmed booking is cancelled.
            category = self.db.get(
                TicketCategory,
                booking.category_id
            )

            if category:
                category.quantity += booking.quantity

            tickets = self.db.query(Ticket).filter(
                Ticket.booking_id == booking.id
            ).all()

            for ticket in tickets:
                ticket.status = "cancelled"

            self.db.commit()

            return {
                "performative": "INFORM",
                "content": {
                    "booking_id": booking.id,
                    "event_id": booking.event_id,
                    "category_id": booking.category_id,
                    "quantity": booking.quantity,
                    "status": booking.status,
                    "refund": refund,
                    "message": (
                        "Booking cancelled. Full refund approved."
                        if refund > 0
                        else "Booking cancelled. No refund is available within 24 hours of the event."
                    )
                }
            }

        except Exception:
            self.db.rollback()
            raise

    def handle_message(self, agent_message):
        if agent_message.get("performative") != "REQUEST":
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "BookingAgent requires REQUEST messages."
                }
            }

        content = agent_message.get("content", {})
        action = content.get("action")

        if action == "CANCEL_BOOKING":
            return self.cancel_booking(
                booking_id=content.get("booking_id"),
                user_id=content.get("user_id")
            )

        if action == "BOOK_WAITLIST_OFFER":
            return self.book_waitlist_offer(
                waitlist_id=content.get("waitlist_id"),
                user_id=content.get("user_id")
            )

        required = [
            "user_id",
            "event_id",
            "category_id",
            "quantity"
        ]

        if any(field not in content for field in required):
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "Missing booking information."
                }
            }

        result = self.book_ticket(
            user_id=content["user_id"],
            event_id=content["event_id"],
            category_id=content["category_id"],
            quantity=content["quantity"]
        )

        performative = result.pop("performative")

        return {
            "performative": performative,
            "content": result
        }
