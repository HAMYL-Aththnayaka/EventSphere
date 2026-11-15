
from datetime import timedelta
from app.models import Event


class VenueAgent:

    def __init__(self, db):
        self.db = db

    def check_venue(self, venue_id, start, end):
        buffer = timedelta(minutes=30)

        existing = self.db.query(Event).filter(
            Event.venue_id == venue_id,
            Event.status == "published",
            Event.start_time < end + buffer,
            Event.end_time > start - buffer
        ).first()

        if existing:
            return {
                "performative": "REFUSE",
                "reason": "Venue is already booked during this time"
            }

        return {
            "performative": "AGREE",
            "reason": "Venue is available"
        }

    def calculate_price(self, venue, start, end):
        hours = (end - start).total_seconds() / 3600
        return hours * venue.hourly_rate
