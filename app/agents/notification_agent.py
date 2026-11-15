
from app.models import Notification


class NotificationAgent:
    def __init__(self, db):
        self.db = db

    def notify(self, user_id, message):
        notification = Notification(
            user_id=user_id,
            message=message
        )

        self.db.add(notification)
        self.db.commit()

        return True

    def handle_message(self, agent_message):
        """Process messages received through the MessageBus."""

        if agent_message["performative"] != "INFORM":
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "NotificationAgent only accepts INFORM messages."
                }
            }

        content = agent_message["content"]

        notifications = content.get("notifications")
        if notifications is None:
            notifications = [{
                "user_id": content.get("user_id"),
                "message": content.get("message")
            }]

        if not notifications or any(
            not item.get("user_id") or not item.get("message")
            for item in notifications
        ):
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "Each notification requires a user_id and message."
                }
            }

        try:
            for item in notifications:
                self.db.add(Notification(
                    user_id=item["user_id"],
                    message=item["message"]
                ))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "performative": "AGREE",
            "content": {
                "message": "Notification(s) saved successfully.",
                "count": len(notifications)
            }
        }
