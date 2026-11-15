
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_roles
from app.models import Venue, VenueHire, User
from app.agents.agent_system import AgentSystem

router = APIRouter(prefix="/hire", tags=["Venue Hire"])


@router.post("/request")
def request_hire(
    venue_id: int,
    start_time: str,
    end_time: str,
    purpose: str,
    guests: int,
    current_user: User = Depends(require_roles("attendee")),
    db: Session = Depends(get_db)
):
    venue = db.get(Venue, venue_id)

    if not venue:
        raise HTTPException(404, "Venue not found.")

    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
    except ValueError:
        raise HTTPException(400, "Invalid date/time format.")

    if end <= start or guests <= 0:
        raise HTTPException(400, "Invalid hire request.")

    if guests > venue.capacity:
        raise HTTPException(400, "Guest count exceeds venue capacity.")

    if not venue.private_hire:
        raise HTTPException(400, "This venue is not available for private hire.")

    system = AgentSystem(db)

    decision = system.check_venue(
        venue_id,
        start,
        end
    )

    decision_content = decision.get("content", {})

    if decision["performative"] == "FAILURE":
        raise HTTPException(500, "VenueAgent could not process the request.")

    price = decision_content.get("estimated_price")

    if price is None:
        hours = (end - start).total_seconds() / 3600
        price = hours * venue.hourly_rate

    status = (
        "confirmed"
        if decision["performative"] == "AGREE"
        else "pending_admin"
    )

    hire = VenueHire(
        user_id=current_user.id,
        venue_id=venue_id,
        start_time=start,
        end_time=end,
        purpose=purpose,
        guests=guests,
        price=price,
        status=status
    )

    try:
        db.add(hire)
        db.commit()
        db.refresh(hire)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Could not save venue hire request.")

    return {
        "hire_id": hire.id,
        "status": status,
        "price": price,
        "reason": decision_content.get(
            "reason",
            "Request processed."
        ),
        "alternatives": []
    }
