
from app.agents.message_bus import MessageBus
from app.agents.booking_agent import BookingAgent
from app.agents.ticket_agent import TicketAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.venue_agent import VenueAgent
from app.agents.waitlist_agent import WaitlistAgent

from app.models import Event, Waitlist


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
        self.bus.subscribe("NotificationAgent")

    def notify(self, user_id, message):
        responses = self.bus.broadcast_inform(
            sender="EventSphere",
            content={
                "user_id": user_id,
                "message": message
            }
        )
        return responses[0] if responses else {
            "performative": "FAILURE",
            "content": {"reason": "No notification listeners are available."}
        }

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

        notification_response = self.notify(
            user_id,
            "Your ticket booking has been confirmed."
        )
        if notification_response["performative"] != "AGREE":
            return notification_response

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
            result = response.get("content", {})

            ticket_response = self.bus.communicate(
                sender="BookingAgent",
                receiver="TicketAgent",
                performative="REQUEST",
                content={
                    "action": "CANCEL_BOOKING_TICKETS",
                    "booking_id": booking_id
                }
            )
            if ticket_response["performative"] != "INFORM":
                return ticket_response

            notification = self.notify(
                user_id,
                result.get("message", "Your booking has been cancelled.")
            )
            if notification["performative"] != "AGREE":
                return notification

            # Offer each released seat to the next person in the queue.
            for _ in range(int(result.get("quantity", 0))):
                self.offer_waitlist_seat(
                    result["event_id"],
                    result["category_id"]
                )

        return response

    def cancel_event(self, event_id):
        response = self.bus.communicate(
            sender="EventSphere",
            receiver="BookingAgent",
            performative="REQUEST",
            content={"action": "CANCEL_EVENT", "event_id": event_id}
        )

        if response["performative"] != "INFORM":
            return response

        cancelled = response.get("content", {}).get("cancelled_bookings", [])
        for booking in cancelled:
            ticket_response = self.bus.communicate(
                sender="BookingAgent",
                receiver="TicketAgent",
                performative="REQUEST",
                content={
                    "action": "CANCEL_BOOKING_TICKETS",
                    "booking_id": booking["booking_id"]
                }
            )
            if ticket_response["performative"] != "INFORM":
                return ticket_response

        notifications = [
            {
                "user_id": booking["user_id"],
                "message": (
                    "The event was cancelled. Your booking was cancelled "
                    f"and a full refund of {booking['refund']:.2f} was approved."
                )
            }
            for booking in cancelled
        ]
        if notifications:
            notification_response = self.bus.broadcast_inform(
                sender="BookingAgent",
                content={"notifications": notifications},
                conversation_id=response["conversation_id"]
            )
            if any(
                item["performative"] != "AGREE"
                for item in notification_response
            ):
                return next(
                    item
                    for item in notification_response
                    if item["performative"] != "AGREE"
                )

        return response

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
        response = self.bus.communicate(
            sender="EventSphere",
            receiver="WaitlistAgent",
            performative="REQUEST",
            content={
                "action": "OFFER_SEAT",
                "event_id": event_id,
                "category_id": category_id
            }
        )

        if response["performative"] == "PROPOSE":
            offer = response["content"]
            event = self.db.get(Event, event_id)
            event_name = event.title if event else "the event"

            notification = self.notify(
                offer["user_id"],
                f"A ticket is available for {event_name}. "
                f"You have 10 minutes to accept your waitlist offer."
            )
            if notification["performative"] != "AGREE":
                return notification

        return response

    def accept_waitlist_offer(self, waitlist_id, user_id):
        booking_response = self.bus.communicate(
            sender="EventSphere",
            receiver="BookingAgent",
            performative="REQUEST",
            content={
                "action": "BOOK_WAITLIST_OFFER",
                "waitlist_id": waitlist_id,
                "user_id": user_id
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

        notification = self.notify(
            user_id,
            "Your waitlist offer was accepted. Your ticket booking is confirmed."
        )
        if notification["performative"] != "AGREE":
            return notification

        return {
            "performative": "AGREE",
            "content": {
                "booking": booking_data,
                "tickets": ticket_response["content"]["tickets"]
            }
        }

    def decline_waitlist_offer(self, waitlist_id, user_id):
        response = self.bus.communicate(
            sender="EventSphere",
            receiver="WaitlistAgent",
            performative="REQUEST",
            content={
                "action": "DECLINE_OFFER",
                "waitlist_id": waitlist_id,
                "user_id": user_id
            }
        )

        if response["performative"] == "INFORM":
            entry = self.db.get(Waitlist, waitlist_id)

            if entry:
                self.offer_waitlist_seat(
                    entry.event_id,
                    entry.category_id
                )

        return response
    
    def expire_waitlist_holds(self):
        response = self.bus.communicate(
            sender="EventSphereScheduler",
            receiver="WaitlistAgent",
            performative="REQUEST",
            content={"action": "EXPIRE_HOLDS"}
        )

        if response["performative"] == "INFORM":
            expired = response.get("content", {}).get("expired", [])

            for entry in expired:
                self.offer_waitlist_seat(
                    entry["event_id"],
                    entry["category_id"]
                )

        return response

    def check_venue(
        self,
        venue_id,
        start,
        end,
        exclude_event_id=None,
        exclude_hire_id=None
    ):
        content = {
            "action": "CHECK_VENUE",
            "venue_id": venue_id,
            "start": start.isoformat(),
            "end": end.isoformat()
        }

        if exclude_event_id is not None:
            content["exclude_event_id"] = exclude_event_id
        if exclude_hire_id is not None:
            content["exclude_hire_id"] = exclude_hire_id

        return self.bus.communicate(
            sender="EventSphere",
            receiver="VenueAgent",
            performative="REQUEST",
            content=content
        )

    def check_hire(self, venue_id, start, end, guests):
        return self.bus.communicate(
            sender="EventSphere",
            receiver="VenueAgent",
            performative="REQUEST",
            content={
                "action": "CHECK_HIRE",
                "venue_id": venue_id,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "guests": guests
            }
        )
