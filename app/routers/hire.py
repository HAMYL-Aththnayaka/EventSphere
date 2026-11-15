from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import Venue, VenueHire
from app.agents.venue_agent import VenueAgent

router = APIRouter(prefix="/hire", tags=["Venue Hire"])


@router.post("/request")
def request_hire(
    user_id: int,
    venue_id: int,
    start_time: str,
    end_time: str,
    purpose: str,
    guests: int,
    db: Session = Depends(get_db)
):

    venue = db.get(Venue, venue_id)

    if not venue:
        raise HTTPException(404, "Venue not found")

    start = datetime.fromisoformat(start_time)
    end = datetime.fromisoformat(end_time)

    if end <= start or guests <= 0:
        raise HTTPException(400, "Invalid request")

    agent = VenueAgent(db)

    price = agent.calculate_price(venue, start_time, end_time)

    available = agent.check_venue(venue_id, start, end)

    if guests > venue.capacity or not venue.private_hire:
        available = {
            "performative": "REFUSE",
            "reason": "Venue is closed for hire or guest count exceeds capacity."
        }

    status = (
        "confirmed"
        if available["performative"] == "AGREE"
        else "pending_admin"
    )

    hire = VenueHire(
        user_id=user_id,
        venue_id=venue_id,
        start_time=start,
        end_time=end,
        purpose=purpose,
        guests=guests,
        price=price,
        status=status
    )

    db.add(hire)
    db.commit()

    return {
        "status": status,
        "price": price,
        "reason": available["reason"],
        "alternatives": []
    }