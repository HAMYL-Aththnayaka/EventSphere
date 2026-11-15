
from datetime import datetime, timedelta

from app.models import Waitlist, Event, TicketCategory


class WaitlistAgent:
    def __init__(self, db):
        self.db = db

    def join(self, user_id, event_id, category_id):
        event = self.db.get(Event, event_id)
        category = self.db.get(TicketCategory, category_id)

        if not event or event.status != "published":
            return None

        if not category or category.event_id != event_id:
            return None

        existing = self.db.query(Waitlist).filter(
            Waitlist.user_id == user_id,
            Waitlist.event_id == event_id,
            Waitlist.category_id == category_id,
            Waitlist.status.in_(["waiting", "offered"])
        ).first()

        if existing:
            return existing

        entry = Waitlist(
            user_id=user_id,
            event_id=event_id,
            category_id=category_id,
            status="waiting"
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        return entry

    def offer_seat(self, event_id, category_id):
        entry = self.db.query(Waitlist).filter(
            Waitlist.event_id == event_id,
            Waitlist.category_id == category_id,
            Waitlist.status == "waiting"
        ).order_by(Waitlist.id).first()

        if not entry:
            return None

        entry.status = "offered"
        entry.hold_until = datetime.utcnow() + timedelta(minutes=10)

        self.db.commit()
        self.db.refresh(entry)

        return entry

    def expire_holds(self):
        now = datetime.utcnow()

        expired = self.db.query(Waitlist).filter(
            Waitlist.status == "offered",
            Waitlist.hold_until < now
        ).all()

        for entry in expired:
            entry.status = "expired"

        self.db.commit()

        return len(expired)

    def handle_message(self, agent_message):
        if agent_message["performative"] != "REQUEST":
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "WaitlistAgent requires REQUEST messages."
                }
            }

        content = agent_message["content"]
        action = content.get("action")

        if action == "JOIN_WAITLIST":
            entry = self.join(
                content.get("user_id"),
                content.get("event_id"),
                content.get("category_id")
            )

            if not entry:
                return {
                    "performative": "REFUSE",
                    "content": {
                        "reason": "Invalid event or ticket category."
                    }
                }

            return {
                "performative": "AGREE",
                "content": {
                    "waitlist_id": entry.id,
                    "status": entry.status
                }
            }

        if action == "OFFER_SEAT":
            entry = self.offer_seat(
                content.get("event_id"),
                content.get("category_id")
            )

            if not entry:
                return {
                    "performative": "REFUSE",
                    "content": {
                        "reason": "No waiting users found."
                    }
                }

            return {
                "performative": "PROPOSE",
                "content": {
                    "waitlist_id": entry.id,
                    "user_id": entry.user_id,
                    "hold_until": entry.hold_until.isoformat()
                }
            }

        if action == "EXPIRE_HOLDS":
            count = self.expire_holds()

            return {
                "performative": "INFORM",
                "content": {
                    "expired_count": count
                }
            }

        return {
            "performative": "REFUSE",
            "content": {
                "reason": "Unknown WaitlistAgent action."
            }
        }
