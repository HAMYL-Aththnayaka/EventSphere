
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_roles
from app.models import Venue, VenueHire, User
from app.agents.agent_system import AgentSystem

router = APIRouter(prefix="/hire", tags=["Venue Hire"])


@router.get("/venues")
def available_venues(db: Session = Depends(get_db)):
    venues = db.query(Venue).filter(
        Venue.private_hire.is_(True)
    ).order_by(Venue.name.asc()).all()

    return [
        {
            "id": venue.id,
            "name": venue.name,
            "location": venue.location,
            "capacity": venue.capacity,
            "hourly_rate": venue.hourly_rate
        }
        for venue in venues
    ]


@router.post("/request")
def request_hire(
    venue_id: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    purpose: str = Form(...),
    guests: int = Form(...),
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

    if start <= datetime.utcnow():
        raise HTTPException(400, "Venue hire must start in the future.")

    purpose = purpose.strip()
    if not purpose:
        raise HTTPException(400, "Please provide a purpose for the hire.")

    if guests > venue.capacity:
        raise HTTPException(400, "Guest count exceeds venue capacity.")

    if not venue.private_hire:
        raise HTTPException(400, "This venue is not available for private hire.")

    system = AgentSystem(db)

    decision = system.check_hire(
        venue_id,
        start,
        end,
        guests
    )

    decision_content = decision.get("content", {})

    if decision["performative"] == "FAILURE":
        raise HTTPException(500, "VenueAgent could not process the request.")

    price = decision_content.get("estimated_price")

    if price is None:
        hours = (end - start).total_seconds() / 3600
        price = hours * venue.hourly_rate

    status = "confirmed" if decision["performative"] == "AGREE" else "pending_admin"

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

    notification = system.notify(
        current_user.id,
        (
            "Your venue hire request was confirmed."
            if status == "confirmed"
            else "Your venue hire request needs admin review. "
            "Review the proposed alternatives in the request response."
        )
    )
    if notification.get("performative") != "AGREE":
        raise HTTPException(
            500,
            "The hire request was saved, but its notification could not be delivered."
        )

    return {
        "hire_id": hire.id,
        "status": status,
        "price": price,
        "message": (
            "Your venue hire was confirmed automatically."
            if status == "confirmed"
            else "Your request needs admin review. The system proposes alternatives."
        ),
        "reason": decision_content.get(
            "reason",
            "Request processed."
        ),
        "alternatives": decision_content.get("alternatives", [])
    }
