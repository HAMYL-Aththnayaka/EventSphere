import secrets

from app.models import Ticket, Booking


class TicketAgent:

    def __init__(self, db):
        self.db = db

    def create_tickets(self, booking):

        tickets = []

        for i in range(booking.quantity):

            code = secrets.token_urlsafe(32)

            ticket = Ticket(
                booking_id=booking.id,
                event_id=booking.event_id,
                code=code,
                status="valid"
            )

            self.db.add(ticket)
            tickets.append(ticket)

        self.db.commit()

        return tickets

    def scan_ticket(self, code, event_id):

        ticket = self.db.query(Ticket).filter(
            Ticket.code == code
        ).with_for_update().first()

        if not ticket:
            return {"result": "REJECTED", "reason": "Invalid ticket"}

        booking = self.db.get(Booking, ticket.booking_id)

        if booking.status != "confirmed" or ticket.status == "cancelled":
            return {"result": "REJECTED", "reason": "Cancelled ticket"}

        if ticket.event_id != event_id:
            return {"result": "REJECTED", "reason": "Wrong event"}

        if ticket.checked_in:
            return {"result": "REJECTED", "reason": "Already used"}

        ticket.checked_in = True
        ticket.status = "used"

        self.db.commit()

        return {"result": "ADMITTED", "reason": "Valid ticket"}