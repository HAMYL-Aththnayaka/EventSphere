
from datetime import datetime, timedelta

from app.models import Event, Venue, VenueHire


class VenueAgent:
    def __init__(self, db):
        self.db = db

    def check_venue(
        self,
        venue_id,
        start,
        end,
        exclude_event_id=None
    ):
        if end <= start:
            return {
                "performative": "REFUSE",
                "reason": "Event end time must be after start time."
            }

        buffer = timedelta(minutes=30)

        # Check published events at this venue.
        event_query = self.db.query(Event).filter(
            Event.venue_id == venue_id,
            Event.status == "published",
            Event.start_time < end + buffer,
            Event.end_time > start - buffer
        )

        # Ignore the event currently being edited or published.
        if exclude_event_id is not None:
            event_query = event_query.filter(
                Event.id != exclude_event_id
            )

        existing_event = event_query.first()

        if existing_event:
            return {
                "performative": "REFUSE",
                "reason": (
                    "Venue is already booked for another event "
                    "during this time."
                )
            }

        # Check confirmed and pending private hires.
        existing_hire = self.db.query(VenueHire).filter(
            VenueHire.venue_id == venue_id,
            VenueHire.status.in_(["confirmed", "pending_admin"]),
            VenueHire.start_time < end + buffer,
            VenueHire.end_time > start - buffer
        ).first()

        if existing_hire:
            return {
                "performative": "REFUSE",
                "reason": (
                    "Venue has an existing private hire "
                    "request during this time."
                )
            }

        return {
            "performative": "AGREE",
            "reason": "Venue is available."
        }

    def calculate_price(self, venue, start, end):
        hours = (end - start).total_seconds() / 3600
        return hours * venue.hourly_rate

    def handle_message(self, agent_message):
        if agent_message["performative"] != "REQUEST":
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "VenueAgent requires REQUEST messages."
                }
            }

        content = agent_message["content"]

        if content.get("action") != "CHECK_VENUE":
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "Unknown VenueAgent action."
                }
            }

        venue_id = content.get("venue_id")
        start = content.get("start")
        end = content.get("end")
        exclude_event_id = content.get("exclude_event_id")

        if not venue_id or not start or not end:
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "Venue ID, start and end are required."
                }
            }

        try:
            start = datetime.fromisoformat(start)
            end = datetime.fromisoformat(end)

            if exclude_event_id is not None:
                exclude_event_id = int(exclude_event_id)

        except (ValueError, TypeError):
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "Invalid date/time or event ID."
                }
            }

        venue = self.db.get(Venue, venue_id)

        if not venue:
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "Venue not found."
                }
            }

        result = self.check_venue(
            venue_id,
            start,
            end,
            exclude_event_id
        )

        if result["performative"] == "REFUSE":
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": result["reason"]
                }
            }

        return {
            "performative": "AGREE",
            "content": {
                "venue_id": venue_id,
                "available": True,
                "reason": result["reason"],
                "estimated_price": self.calculate_price(
                    venue, start, end
                )
            }
        }
