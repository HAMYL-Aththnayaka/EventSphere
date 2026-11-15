import uuid

from app.models import Booking, TicketCategory


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
            TicketCategory.id == category_id
        ).with_for_update().first()

        if not category or category.event_id != event_id:
            return {
                "performative": "REFUSE",
                "reason": "Invalid ticket category."
            }

        # Conditional update prevents overselling.
        from sqlalchemy import update

        result = self.db.execute(
            update(TicketCategory)
            .where(
                TicketCategory.id == category_id,
                TicketCategory.quantity >= quantity
            )
            .values(quantity=TicketCategory.quantity - quantity)
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

        return {
            "performative": "AGREE",
            "booking_id": booking.id,
            "total": total,
            "payment_reference": booking.payment_reference
        }

    def cancel_booking(self, booking, event):

        if booking.status != "confirmed":
            return {"performative": "REFUSE", "reason": "Already cancelled."}

        from datetime import datetime, timedelta

        booking.status = "cancelled"

        if event.start_time > datetime.utcnow() + timedelta(hours=24):
            refund = booking.total

            category = self.db.get(
                TicketCategory, booking.category_id
            )
            category.quantity += booking.quantity
        else:
            refund = 0

        self.db.commit()

        return {
            "performative": "INFORM",
            "refund": refund
        }