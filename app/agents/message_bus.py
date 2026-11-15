
import json
import uuid

from app.models import AgentMessage


class MessageBus:
    """Send structured messages between agents and log them."""

    VALID_PERFORMATIVES = {
        "REQUEST",
        "AGREE",
        "REFUSE",
        "PROPOSE",
        "INFORM",
        "FAILURE"
    }

    def __init__(self, db):
        self.db = db

    def send(
        self,
        sender: str,
        receiver: str,
        performative: str,
        content: dict,
        conversation_id: str | None = None
    ) -> dict:
        """Create a JSON message and persist it in the database."""

        if performative not in self.VALID_PERFORMATIVES:
            raise ValueError(f"Invalid performative: {performative}")

        if not isinstance(content, dict):
            raise TypeError("Message content must be a dictionary.")

        conversation_id = conversation_id or str(uuid.uuid4())

        message = {
            "sender": sender,
            "receiver": receiver,
            "performative": performative,
            "content": content,
            "conversation_id": conversation_id
        }

        log = AgentMessage(
            conversation_id=conversation_id,
            sender=sender,
            receiver=receiver,
            performative=performative,
            content=json.dumps(content)
        )

        try:
            self.db.add(log)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return message



messageBus = MessageBus