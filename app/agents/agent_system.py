from app.agents.message_bus import MessageBus
from app.agents.booking_agent import BookingAgent
from app.agents.ticket_agent import TicketAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.venue_agent import VenueAgent
from app.agents.waitlist_agent import WaitlistAgent


class AgentSystem:
    def __init__(self, db):
        self.db = db
        self.bus = MessageBus(db)

        self.booking_agent = BookingAgent(db)
        self.ticket_agent = TicketAgent(db)
        self.notification_agent = NotificationAgent(db)
        self.venue_agent = VenueAgent(db)
        self.waitlist_agent = WaitlistAgent(db)

        self.bus.register("BookingAgent", self.booking_agent.handle_message)
        self.bus.register("TicketAgent", self.ticket_agent.handle_message)
        self.bus.register("NotificationAgent", self.notification_agent.handle_message)
        self.bus.register("VenueAgent", self.venue_agent.handle_message)
        self.bus.register("WaitlistAgent", self.waitlist_agent.handle_message)

    def book_tickets(self, user_id, event_id, category_id, quantity):
        booking_response = self.bus.communicate(
            sender="EventSphere",
            receiver="BookingAgent",
            performative="REQUEST",
            content={
                "user_id": user_id,
                "event_id": event_id,
                "category_id": category_id,
                "quantity": quantity
            }
        )

        if booking_response["performative"] != "AGREE":
            return booking_response

        booking_data = booking_response["content"]

        ticket_response = self.bus.communicate(
            sender="BookingAgent",
            receiver="TicketAgent",
            performative="REQUEST",
            content={
                "action": "CREATE_TICKETS",
                "booking_id": booking_data["booking_id"]
            }
        )

        if ticket_response["performative"] != "AGREE":
            return ticket_response

        notification_response = self.bus.communicate(
            sender="BookingAgent",
            receiver="NotificationAgent",
            performative="INFORM",
            content={
                "user_id": user_id,
                "message": "Your ticket booking has been confirmed."
            }
        )

        return {
            "performative": "AGREE",
            "content": {
                "booking": booking_data,
                "tickets": ticket_response["content"]["tickets"],
                "notification": notification_response["performative"]
            }
        }

    def cancel_booking(self, booking_id, user_id):
        response = self.bus.communicate(
            sender="EventSphere",
            receiver="BookingAgent",
            performative="REQUEST",
            content={
                "action": "CANCEL_BOOKING",
                "booking_id": booking_id,
                "user_id": user_id
            }
        )

        if response["performative"] == "INFORM":
            self.bus.communicate(
                sender="BookingAgent",
                receiver="NotificationAgent",
                performative="INFORM",
                content={
                    "user_id": user_id,
                    "message": "Your booking has been cancelled."
                }
            )

        return response

    def check_venue(self, venue_id, start, end):
        return self.bus.communicate(
            sender="EventSphere",
            receiver="VenueAgent",
            performative="REQUEST",
            content={
                "action": "CHECK_VENUE",
                "venue_id": venue_id,
                "start": start.isoformat(),
                "end": end.isoformat()
            }
        )

    def join_waitlist(self, user_id, event_id, category_id):
        return self.bus.communicate(
            sender="EventSphere",
            receiver="WaitlistAgent",
            performative="REQUEST",
            content={
                "action": "JOIN_WAITLIST",
                "user_id": user_id,
                "event_id": event_id,
                "category_id": category_id
            }
        )

    def offer_waitlist_seat(self, event_id, category_id):
        return self.bus.communicate(
            sender="EventSphere",
            receiver="WaitlistAgent",
            performative="REQUEST",
            content={
                "action": "OFFER_SEAT",
                "event_id": event_id,
                "category_id": category_id
            }
        )