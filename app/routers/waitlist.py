
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.database import get_db
from app.models import User, Waitlist, Event, TicketCategory
from app.agents.agent_system import AgentSystem


router = APIRouter(prefix="/waitlist", tags=["Waitlist"])


@router.post("/join")
def join_waitlist(
    event_id: int = Form(...),
    category_id: int = Form(...),
    current_user: User = Depends(require_roles("attendee")),
    db: Session = Depends(get_db)
):
    result = AgentSystem(db).join_waitlist(
        current_user.id,
        event_id,
        category_id
    )

    if result["performative"] != "AGREE":
        raise HTTPException(
            status_code=400,
            detail=result.get("content", {}).get(
                "reason",
                "Could not join the waitlist."
            )
        )

    return {
        "message": "You have joined the waitlist.",
        **result["content"]
    }


@router.get("/my")
def my_waitlist(
    current_user: User = Depends(require_roles("attendee")),
    db: Session = Depends(get_db)
):
    entries = db.query(Waitlist).filter(
        Waitlist.user_id == current_user.id
    ).order_by(Waitlist.id.desc()).all()

    result = []

    for entry in entries:
        event = db.get(Event, entry.event_id)
        category = db.get(TicketCategory, entry.category_id)

        result.append({
            "id": entry.id,
            "event_id": entry.event_id,
            "event_title": event.title if event else "Unavailable event",
            "category_name": category.name if category else "Ticket",
            "status": entry.status,
            "hold_until": (
                entry.hold_until.isoformat()
                if entry.hold_until else None
            )
        })

    return {"waitlist": result}


@router.post("/{waitlist_id}/accept")
def accept_waitlist_offer(
    waitlist_id: int,
    current_user: User = Depends(require_roles("attendee")),
    db: Session = Depends(get_db)
):
    result = AgentSystem(db).accept_waitlist_offer(
        waitlist_id,
        current_user.id
    )

    if result["performative"] != "AGREE":
        raise HTTPException(
            status_code=400,
            detail=result.get("content", {}).get(
                "reason",
                "Could not accept this offer."
            )
        )

    return {
        "message": "Waitlist offer accepted. Your booking is confirmed.",
        **result["content"]
    }


@router.post("/{waitlist_id}/decline")
def decline_waitlist_offer(
    waitlist_id: int,
    current_user: User = Depends(require_roles("attendee")),
    db: Session = Depends(get_db)
):
    result = AgentSystem(db).decline_waitlist_offer(
        waitlist_id,
        current_user.id
    )

    if result["performative"] != "INFORM":
        raise HTTPException(
            status_code=400,
            detail=result.get("content", {}).get(
                "message",
                "Could not decline this offer."
            )
        )

    return result["content"]
