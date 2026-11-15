
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.database import get_db
from app.models import (
    Venue,
    Event,
    TicketCategory,
    VenueHire,
    User,
    Booking
)
from app.security import hash_password
from app.agents.agent_system import AgentSystem


router = APIRouter(prefix="/admin", tags=["Admin"])


# =====================================================
# VENUE MANAGEMENT
# =====================================================

@router.post("/venues")
@router.post("/venue")
def create_venue(
    name: str,
    location: str,
    capacity: int,
    hourly_rate: float,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    name = name.strip()
    location = location.strip()

    if not name or not location:
        raise HTTPException(400, "Venue name and location are required.")

    if capacity <= 0 or hourly_rate < 0:
        raise HTTPException(400, "Invalid venue details.")

    venue = Venue(
        name=name,
        location=location,
        capacity=capacity,
        hourly_rate=hourly_rate,
        description="",
        image="",
        private_hire=True
    )

    db.add(venue)
    db.commit()
    db.refresh(venue)

    return {
        "message": "Venue created successfully.",
        "venue_id": venue.id
    }


@router.get("/events")
def get_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    events = db.query(Event).order_by(Event.id.desc()).all()

    result = []

    for event in events:
        ticket_categories = (
            db.query(TicketCategory)
            .filter(TicketCategory.event_id == event.id)
            .all()
        )

        result.append({
            "id": event.id,
            "title": event.title,
            "category": event.category,
            "venue_id": event.venue_id,
            "start_time": (
                event.start_time.isoformat()
                if event.start_time else ""
            ),
            "end_time": (
                event.end_time.isoformat()
                if event.end_time else ""
            ),
            "description": event.description,
            "status": event.status,
            "ticket_categories": [
                {
                    "id": ticket.id,
                    "name": ticket.name,
                    "price": ticket.price,
                    "quantity": ticket.quantity
                }
                for ticket in ticket_categories
            ]
        })

    return result


@router.put("/venue/{venue_id}")
def update_venue(
    venue_id: int,
    name: str,
    location: str,
    capacity: int,
    hourly_rate: float,
    description: str = "",
    image: str = "",
    private_hire: bool = True,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    venue = db.get(Venue, venue_id)

    if not venue:
        raise HTTPException(404, "Venue not found.")

    name = name.strip()
    location = location.strip()

    if not name or not location:
        raise HTTPException(400, "Venue name and location are required.")

    if capacity <= 0 or hourly_rate < 0:
        raise HTTPException(400, "Invalid venue details.")

    venue.name = name
    venue.location = location
    venue.capacity = capacity
    venue.hourly_rate = hourly_rate
    venue.description = description
    venue.image = image
    venue.private_hire = private_hire

    db.commit()
    db.refresh(venue)

    return {
        "message": "Venue updated successfully.",
        "venue_id": venue.id
    }


# =====================================================
# EVENT MANAGEMENT
# =====================================================

@router.post("/event")
def create_event(
    title: str,
    category: str,
    venue_id: int,
    start_time: str,
    end_time: str,
    description: str,
    ticket_name: str,
    price: float,
    quantity: int,
    current_user: User = Depends(require_roles("admin")),
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

    if end <= start:
        raise HTTPException(400, "Invalid event time.")

    if quantity <= 0 or quantity > venue.capacity or price < 0:
        raise HTTPException(400, "Invalid ticket quantity or price.")

    system = AgentSystem(db)
    decision = system.check_venue(venue_id, start, end)

    decision_content = decision.get("content", {})

    event = Event(
        title=title,
        category=category,
        venue_id=venue_id,
        start_time=start,
        end_time=end,
        description=description,
        status=(
            "published"
            if decision.get("performative") == "AGREE"
            else "draft"
        )
    )

    try:
        db.add(event)
        db.commit()
        db.refresh(event)

        ticket = TicketCategory(
            event_id=event.id,
            name=ticket_name,
            price=price,
            quantity=quantity
        )

        db.add(ticket)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(500, "Could not create event.")

    return {
        "message": "Event created successfully.",
        "event_id": event.id,
        "status": event.status,
        "reason": decision_content.get(
            "reason",
            "Venue decision unavailable."
        )
    }



@router.put("/event/{event_id}")
def update_event(
    event_id: int,
    title: str,
    category: str,
    venue_id: int,
    start_time: str,
    end_time: str,
    description: str,
    ticket_name: str,
    price: float,
    quantity: int,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    event = db.get(Event, event_id)

    if not event:
        raise HTTPException(404, "Event not found.")

    venue = db.get(Venue, venue_id)

    if not venue:
        raise HTTPException(404, "Venue not found.")

    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
    except ValueError:
        raise HTTPException(400, "Invalid date/time format.")

    if end <= start:
        raise HTTPException(400, "Invalid event time.")

    if quantity <= 0 or quantity > venue.capacity or price < 0:
        raise HTTPException(400, "Invalid ticket quantity or price.")

    ticket = db.query(TicketCategory).filter(
        TicketCategory.event_id == event_id
    ).first()

    if not ticket:
        raise HTTPException(404, "Ticket category not found.")

    bookings = db.query(Booking).filter(
        Booking.category_id == ticket.id,
        Booking.status == "confirmed"
    ).all()

    sold = sum(booking.quantity for booking in bookings)

    if quantity < sold:
        raise HTTPException(
            400,
            f"Cannot reduce quantity below {sold} already-booked tickets."
        )

    # Published events must pass the VenueAgent availability check.
    # Draft events are checked when the admin publishes them.
    if event.status == "published":
        system = AgentSystem(db)

        decision = system.check_venue(
            venue_id,
            start,
            end,
            exclude_event_id=event.id
        )

        if decision.get("performative") != "AGREE":
            reason = decision.get("content", {}).get(
                "reason",
                "Venue is unavailable."
            )
            raise HTTPException(409, reason)

    event.title = title
    event.category = category
    event.venue_id = venue_id
    event.start_time = start
    event.end_time = end
    event.description = description

    ticket.name = ticket_name
    ticket.price = price
    ticket.quantity = quantity

    try:
        db.commit()
        db.refresh(event)

    except Exception:
        db.rollback()
        raise HTTPException(500, "Could not update event.")

    return {
        "message": "Event updated successfully.",
        "event_id": event.id
    }



@router.post("/event/{event_id}/status")
def update_event_status(
    event_id: int,
    status: str,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    if status not in ["draft", "published", "cancelled"]:
        raise HTTPException(400, "Invalid event status.")

    event = db.get(Event, event_id)

    if not event:
        raise HTTPException(404, "Event not found.")

    if status == "published":
        venue = db.get(Venue, event.venue_id)

        if not venue:
            raise HTTPException(404, "Event venue not found.")

        total_capacity = sum(
            category.quantity
            for category in db.query(TicketCategory).filter(
                TicketCategory.event_id == event.id
            ).all()
        )

        if total_capacity <= 0 or total_capacity > venue.capacity:
            raise HTTPException(
                400,
                "Ticket capacity is invalid or exceeds venue capacity."
            )

        system = AgentSystem(db)

        decision = system.check_venue(
            event.venue_id,
            event.start_time,
            event.end_time,
            exclude_event_id=event.id
        )

        if decision.get("performative") != "AGREE":
            reason = decision.get("content", {}).get(
                "reason",
                "Venue is unavailable."
            )
            raise HTTPException(409, reason)

    event.status = status
    db.commit()

    return {
        "message": "Event status updated.",
        "event_id": event.id,
        "status": event.status
    }


# =====================================================
# PRIVATE VENUE HIRE MANAGEMENT
# =====================================================

@router.get("/hires")
def get_hire_requests(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    return db.query(VenueHire).order_by(
        VenueHire.id.desc()
    ).all()


@router.post("/hire/{hire_id}/decision")
def decide_hire_request(
    hire_id: int,
    decision: str,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    if decision not in ["approve", "reject"]:
        raise HTTPException(
            400,
            "Decision must be approve or reject."
        )

    hire = db.get(VenueHire, hire_id)

    if not hire:
        raise HTTPException(404, "Hire request not found.")

    if hire.status != "pending_admin":
        raise HTTPException(
            400,
            "This hire request is not awaiting approval."
        )

    if decision == "reject":
        hire.status = "rejected"

    else:
        system = AgentSystem(db)

        availability = system.check_venue(
            hire.venue_id,
            hire.start_time,
            hire.end_time
        )

        if availability.get("performative") != "AGREE":
            reason = availability.get("content", {}).get(
                "reason",
                "Venue is no longer available."
            )
            raise HTTPException(409, reason)

        hire.status = "confirmed"

    db.commit()

    return {
        "message": "Hire request decision saved.",
        "hire_id": hire.id,
        "status": hire.status
    }


# =====================================================
# STAFF ACCOUNT MANAGEMENT
# =====================================================

@router.post("/staff")
def create_staff(
    name: str,
    email: str,
    password: str,
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    name = name.strip()
    email = email.strip().lower()

    if not name or len(name) > 100:
        raise HTTPException(400, "Please enter a valid staff name.")

    if len(email) > 100 or "@" not in email:
        raise HTTPException(400, "Please enter a valid email address.")

    if len(password) < 8:
        raise HTTPException(
            400,
            "Password must contain at least 8 characters."
        )

    existing = db.query(User).filter(
        User.email == email
    ).first()

    if existing:
        raise HTTPException(
            409,
            "An account with this email already exists."
        )

    staff = User(
        name=name,
        email=email,
        password=hash_password(password),
        role="staff"
    )

    try:
        db.add(staff)
        db.commit()
        db.refresh(staff)

    except Exception:
        db.rollback()
        raise HTTPException(500, "Could not create staff account.")

    return {
        "message": "Staff account created successfully.",
        "staff": {
            "id": staff.id,
            "name": staff.name,
            "email": staff.email,
            "role": staff.role
        }
    }


@router.get("/staff")
def get_staff(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    staff_members = (
        db.query(User)
        .filter(User.role == "staff")
        .order_by(User.id.desc())
        .all()
    )

    return [
        {
            "id": staff.id,
            "name": staff.name,
            "email": staff.email,
            "role": staff.role
        }
        for staff in staff_members
    ]

@router.get("/venues")
def get_venues(
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db)
):
    venues = db.query(Venue).order_by(Venue.id.desc()).all()

    return [
        {
            "id": venue.id,
            "name": venue.name,
            "location": venue.location,
            "capacity": venue.capacity,
            "hourly_rate": venue.hourly_rate,
            "description": venue.description,
            "image": venue.image,
            "private_hire": venue.private_hire
        }
        for venue in venues
    ]