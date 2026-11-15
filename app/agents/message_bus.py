
import json
import uuid

from app.models import AgentMessage


class MessageBus:
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
        self.handlers = {}

    def register(self, agent_name, handler):
        """Register an agent's message handler."""
        self.handlers[agent_name] = handler

    def send(
        self,
        sender,
        receiver,
        performative,
        content,
        conversation_id=None
    ):
        """Create and persist a structured agent message."""

        if not sender or not receiver:
            raise ValueError("Sender and receiver are required.")

        if performative not in self.VALID_PERFORMATIVES:
            raise ValueError("Invalid message performative.")

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

    def dispatch(self, message):
        """Deliver a message to its registered receiving agent."""

        receiver = message["receiver"]
        sender = message["sender"]
        conversation_id = message["conversation_id"]

        handler = self.handlers.get(receiver)

        if handler is None:
            return self.send(
                sender=receiver,
                receiver=sender,
                performative="FAILURE",
                content={
                    "error": f"Agent '{receiver}' is not registered."
                },
                conversation_id=conversation_id
            )

        try:
            result = handler(message)

            if not isinstance(result, dict):
                result = {
                    "performative": "INFORM",
                    "content": {"result": str(result)}
                }

            performative = result.get("performative", "INFORM")
            content = result.get("content", result)

            return self.send(
                sender=receiver,
                receiver=sender,
                performative=performative,
                content=content,
                conversation_id=conversation_id
            )

        except Exception as error:
            self.db.rollback()

            return self.send(
                sender=receiver,
                receiver=sender,
                performative="FAILURE",
                content={"error": str(error)},
                conversation_id=conversation_id
            )


    def communicate(
        self,
        sender,
        receiver,
        content,
        conversation_id=None,
        performative="REQUEST"
    ):
        """Send a message and deliver it through the message bus."""

        message = self.send(
            sender=sender,
            receiver=receiver,
            performative=performative,
            content=content,
            conversation_id=conversation_id
        )

        return self.dispatch(message)


    def receive(self, receiver, conversation_id=None):
        """Retrieve messages addressed to an agent."""

        query = self.db.query(AgentMessage).filter(
            AgentMessage.receiver == receiver
        )

        if conversation_id:
            query = query.filter(
                AgentMessage.conversation_id == conversation_id
            )

        messages = query.order_by(AgentMessage.id.asc()).all()

        return [
            {
                "sender": item.sender,
                "receiver": item.receiver,
                "performative": item.performative,
                "content": json.loads(item.content),
                "conversation_id": item.conversation_id
            }
            for item in messages
        ]


messageBus = MessageBus
