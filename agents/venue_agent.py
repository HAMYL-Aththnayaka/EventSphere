from datetime import timedelta
from app.models import Events

class VenueAgents:
    def __init__(self,db):
        self.db = db

    def check_venue(self,venue_id,start,end):
        buffer = timedelta(minutes=30)

        existing = self.db.query(Event).filter(
            Event.venue_id == venue_id,
            Event.status == "published",
            Event.start_time < end +buffer,
            Event.end_time > start - buffer
        ).first()

        if existing:
            return{
                "performative":"REFUSE",
                "reason":"Venue is already booked durrring this time"
            }

        return{
            "performative":"AGREE",
            "reason":"Venue is availble"
        }

    def calculate_price():
        hours = (end - start).total_seconds() /3600 
        return hours  * venue.hourly_rate;