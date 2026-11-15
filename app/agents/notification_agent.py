
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

        user_id = content.get("user_id")
        message = content.get("message")

        if not user_id or not message:
            return {
                "performative": "REFUSE",
                "content": {
                    "reason": "user_id and message are required."
                }
            }

        self.notify(user_id, message)

        return {
            "performative": "AGREE",
            "content": {
                "message": "Notification saved successfully.",
                "user_id": user_id
            }
        }
