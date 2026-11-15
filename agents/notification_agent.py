from app.models import Notification

class NotificationAgent:
    def __init__(self,db):
        self.db =db

    def notify(self,user_id,message):
        notification = Notification(
            user_id=user_id,
            message = message
        )
        self.db.add(notification)
        self.db.commit()

        return True