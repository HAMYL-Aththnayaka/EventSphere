
from datetime import datetime, timedelta

from sqlalchemy import update

from app.models import Waitlist, Event, TicketCategory


class WaitlistAgent:
    def __init__(self, db):
        self.db = db

    def join(self, user_id, event_id, category_id):
        event = self.db.get(Event, event_id)

        category = self.db.query(TicketCategory).filter(
            TicketCategory.id == category_id,
            TicketCategory.event_id == event_id
        ).first()

        if not event or event.status != "published":
            return None, "This event is not available."

        if not category:
            return None, "Invalid ticket category."

        existing = self.db.query(Waitlist).filter(
            Waitlist.user_id == user_id,
            Waitlist.event_id == event_id,
            Waitlist.category_id == category_id,
            Waitlist.status.in_(["waiting", "offered"])
        ).first()

        if existing:
            return existing, None

        entry = Waitlist(
            user_id=user_id,
            event_id=event_id,
            category_id=category_id,
            status="waiting"
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        return entry, None

    def offer_seat(self, event_id, category_id):
        entry = self.db.query(Waitlist).filter(
            Waitlist.event_id == event_id,
            Waitlist.category_id == category_id,
            Waitlist.status == "waiting"
        ).order_by(Waitlist.id.asc()).first()

        if not entry:
            return None

        event = self.db.get(Event, event_id)

        if not event or event.status != "published":
            return None

        try:
            # Atomically reserve one available ticket.
            reservation = self.db.execute(
                update(TicketCategory)
                .where(
                    TicketCategory.id == category_id,
                    TicketCategory.event_id == event_id,
                    TicketCategory.quantity >= 1
                )
                .values(
                    quantity=TicketCategory.quantity - 1
                )
            )

            if reservation.rowcount == 0:
                self.db.rollback()
                return None

            # Only one process can offer this waiting entry.
            offered = self.db.execute(
                update(Waitlist)
                .where(
                    Waitlist.id == entry.id,
                    Waitlist.status == "waiting"
                )
                .values(
                    status="offered",
                    hold_until=datetime.utcnow() + timedelta(minutes=10)
                )
            )

            if offered.rowcount == 0:
                self.db.rollback()
                return None

            self.db.commit()
            self.db.refresh(entry)

            return entry

        except Exception:
            self.db.rollback()
            raise

    def decline_offer(self, waitlist_id, user_id):
        entry = self.db.query(Waitlist).filter(
            Waitlist.id == waitlist_id,
            Waitlist.user_id == user_id
        ).first()

        if not entry or entry.status != "offered":
            return False, "This offer is no longer active."

        try:
            result = self.db.execute(
                update(Waitlist)
                .where(
                    Waitlist.id == waitlist_id,
                    Waitlist.user_id == user_id,
                    Waitlist.status == "offered"
                )
                .values(status="declined")
            )

            if result.rowcount == 0:
                self.db.rollback()
                return False, "This offer is no longer active."

            category = self.db.get(
                TicketCategory,
                entry.category_id
            )

            if category:
                category.quantity += 1

            self.db.commit()

            return True, "Offer declined."

        except Exception:
            self.db.rollback()
            raise

    def expire_holds(self):
        now = datetime.utcnow()

        expired_entries = self.db.query(Waitlist).filter(
            Waitlist.status == "offered",
            Waitlist.hold_until <= now
        ).all()

        expired = []

        try:
            for entry in expired_entries:
                result = self.db.execute(
                    update(Waitlist)
                    .where(
                        Waitlist.id == entry.id,
                        Waitlist.status == "offered",
                        Waitlist.hold_until <= now
                    )
                    .values(status="expired")
                )

                if result.rowcount == 0:
                    continue

                category = self.db.get(
                    TicketCategory,
                    entry.category_id
                )

                if category:
                    category.quantity += 1

                expired.append({
                    "waitlist_id": entry.id,
                    "event_id": entry.event_id,
                    "category_id": entry.category_id,
                    "user_id": entry.user_id
                })

            self.db.commit()

            return expired

        except Exception:
            self.db.rollback()
            raise

    def handle_message(self, agent_message):
        if agent_message.get("performative") != "REQUEST":
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "WaitlistAgent requires REQUEST messages."
                }
            }

        content = agent_message.get("content", {})
        action = content.get("action")

        if action == "JOIN_WAITLIST":
            entry, error = self.join(
                content.get("user_id"),
                content.get("event_id"),
                content.get("category_id")
            )

            if error:
                return {
                    "performative": "REFUSE",
                    "content": {"reason": error}
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
                        "reason": "No waiting user or available seat found."
                    }
                }

            return {
                "performative": "PROPOSE",
                "content": {
                    "waitlist_id": entry.id,
                    "user_id": entry.user_id,
                    "event_id": entry.event_id,
                    "category_id": entry.category_id,
                    "hold_until": entry.hold_until.isoformat()
                }
            }

        if action == "DECLINE_OFFER":
            success, message = self.decline_offer(
                content.get("waitlist_id"),
                content.get("user_id")
            )

            return {
                "performative": "INFORM" if success else "REFUSE",
                "content": {"message": message}
            }

        if action == "EXPIRE_HOLDS":
            expired = self.expire_holds()

            return {
                "performative": "INFORM",
                "content": {
                    "expired": expired,
                    "expired_count": len(expired)
                }
            }

        return {
            "performative": "REFUSE",
            "content": {
                "reason": "Unknown WaitlistAgent action."
            }
        }
