from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.agents.waitlist_agent import WaitlistAgent

router = APIRouter(prefix="/waitlist", tags=["Waitlist"])


@router.post("/join")
def join_waitlist(
    user_id: int,
    event_id: int,
    category_id: int,
    db: Session = Depends(get_db)
):

    agent = WaitlistAgent(db)

    entry = agent.join(
        user_id,
        event_id,
        category_id
    )

    return {
        "message": "Added to waitlist",
        "waitlist_id": entry.id
    }