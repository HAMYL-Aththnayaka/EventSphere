
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_roles
from app.models import User
from app.agents.agent_system import AgentSystem

router = APIRouter(prefix="/scanner", tags=["Scanner"])


@router.post("/check")
def scan_ticket(
    code: str,
    event_id: int,
    current_user: User = Depends(require_roles("staff", "admin")),
    db: Session = Depends(get_db)
):
    if not code.strip():
        raise HTTPException(status_code=400, detail="Ticket code is required.")

    if event_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid event ID.")

    try:
        system = AgentSystem(db)

        response = system.bus.communicate(
            sender="EventSphere",
            receiver="TicketAgent",
            performative="REQUEST",
            content={
                "action": "SCAN_TICKET",
                "code": code.strip(),
                "event_id": event_id
            }
        )

        if not response or response.get("performative") == "FAILURE":
            raise HTTPException(
                status_code=(
                    500
                    if response.get("performative") == "FAILURE"
                    else 400
                ),
                detail=response.get("content", "Ticket validation failed.")
                if response else "No response from TicketAgent."
            )

        return response.get("content", response)

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Scanner error: {str(error)}"
        )
