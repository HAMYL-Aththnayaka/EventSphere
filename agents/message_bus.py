import uuid
import json

from app.models import AgentMessage

class messageBus:
    def __init__(self,db):
        self.db = db

    def send(self,sender,reciever,performative,content):
        conversation_id = str(uuid.uuid4())

        message = {
            "sender": sender,
            "receiver": receiver,
            "performative": performative,
            "content": content,
            "conversation_id": conversation_id
        }

        log = AgentMessage(
            conversation_id = conversation_id,
            sender = sender,
            reciever=reciever,
            performative = performative,
            content=json.dumps(content)
        )
        self.db.add(log)
        self.db.commit()

        return message