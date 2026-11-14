from datetime import datetime, timedelta

from app.models import Waitlist


class WaitlistAgent:

    def __init__(self, db):
        self.db = db

    def join(self, user_id, event_id, category_id):

        entry = Waitlist(
            user_id=user_id,
            event_id=event_id,
            category_id=category_id
        )

        self.db.add(entry)
        self.db.commit()

        return entry

    def offer_seat(self, event_id, category_id):

        entry = self.db.query(Waitlist).filter(
            Waitlist.event_id == event_id,
            Waitlist.category_id == category_id,
            Waitlist.status == "waiting"
        ).order_by(Waitlist.id).first()

        if entry:
            entry.status = "offered"
            entry.hold_until = datetime.utcnow() + timedelta(minutes=10)
            self.db.commit()

            return entry

        return None

    def expire_holds(self):

        now = datetime.utcnow()

        expired = self.db.query(Waitlist).filter(
            Waitlist.status == "offered",
            Waitlist.hold_until < now
        ).all()

        for entry in expired:
            entry.status = "expired"

        self.db.commit()