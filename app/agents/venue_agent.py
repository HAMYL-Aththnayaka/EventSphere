
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
        exclude_event_id=None,
        exclude_hire_id=None
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
        hire_query = self.db.query(VenueHire).filter(
            VenueHire.venue_id == venue_id,
            VenueHire.status.in_(["confirmed", "pending_admin"]),
            VenueHire.start_time < end + buffer,
            VenueHire.end_time > start - buffer
        )
        if exclude_hire_id is not None:
            hire_query = hire_query.filter(VenueHire.id != exclude_hire_id)
        existing_hire = hire_query.first()

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

    def suggest_alternatives(self, venue, start, end, guests):
        duration = end - start
        alternatives = []

        other_venues = self.db.query(Venue).filter(
            Venue.id != venue.id,
            Venue.private_hire.is_(True),
            Venue.capacity >= guests
        ).order_by(Venue.id.asc()).all()

        for candidate in other_venues:
            result = self.check_venue(
                candidate.id,
                start,
                end
            )
            if result["performative"] == "AGREE":
                alternatives.append({
                    "venue_id": candidate.id,
                    "venue_name": candidate.name,
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                    "price": self.calculate_price(candidate, start, end)
                })
                if len(alternatives) == 3:
                    return alternatives

        for day in range(1, 8):
            alternative_start = start + timedelta(days=day)
            alternative_end = alternative_start + duration
            result = self.check_venue(
                venue.id,
                alternative_start,
                alternative_end
            )
            if result["performative"] == "AGREE":
                alternatives.append({
                    "venue_id": venue.id,
                    "venue_name": venue.name,
                    "start_time": alternative_start.isoformat(),
                    "end_time": alternative_end.isoformat(),
                    "price": self.calculate_price(
                        venue,
                        alternative_start,
                        alternative_end
                    )
                })
                if len(alternatives) == 3:
                    break

        return alternatives

    def handle_message(self, agent_message):
        if agent_message["performative"] != "REQUEST":
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "VenueAgent requires REQUEST messages."
                }
            }

        content = agent_message["content"]

        action = content.get("action")
        if action not in ["CHECK_VENUE", "CHECK_HIRE"]:
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
        exclude_hire_id = content.get("exclude_hire_id")
        guests = content.get("guests")

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
            if exclude_hire_id is not None:
                exclude_hire_id = int(exclude_hire_id)
            if guests is not None:
                guests = int(guests)

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

        if action == "CHECK_HIRE":
            if not venue.private_hire:
                return {
                    "performative": "REFUSE",
                    "content": {
                        "reason": "This venue is not available for private hire."
                    }
                }
            if guests is None or guests <= 0 or guests > venue.capacity:
                return {
                    "performative": "REFUSE",
                    "content": {
                        "reason": "Guest count must be within venue capacity."
                    }
                }

        result = self.check_venue(
            venue_id,
            start,
            end,
            exclude_event_id,
            exclude_hire_id
        )

        if result["performative"] == "REFUSE":
            if action == "CHECK_HIRE":
                alternatives = self.suggest_alternatives(
                    venue,
                    start,
                    end,
                    guests
                )
                if alternatives:
                    return {
                        "performative": "PROPOSE",
                        "content": {
                            "reason": result["reason"],
                            "alternatives": alternatives
                        }
                    }
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
