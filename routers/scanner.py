from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.agents.ticket_agent import TicketAgent

router = APIRouter(prefix="/scanner", tags=["Scanner"])


@router.post("/check")
def scan_ticket(
    code: str,
    event_id: int,
    db: Session = Depends(get_db)
):

    agent = TicketAgent(db)

    return agent.scan_ticket(code, event_id)