
import pytest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import (
    User,
    Venue,
    Event,
    TicketCategory,
    Booking,
    Ticket,
    Waitlist,
    VenueHire,
    Notification,
    AgentMessage
)
from app.agents.agent_system import AgentSystem


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    Base.metadata.create_all(bind=engine)

    TestingSession = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    session = TestingSession()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def event_data(db):
    user = User(
        name="Test User",
        email="test@example.com",
        password="test-password",
        role="attendee"
    )

    venue = Venue(
        name="Test Venue",
        location="Test Location",
        capacity=100,
        hourly_rate=500,
        private_hire=True
    )

    db.add_all([user, venue])
    db.commit()
    db.refresh(user)
    db.refresh(venue)

    now = datetime.utcnow()

    event = Event(
        title="Test Event",
        category="Technology",
        venue_id=venue.id,
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        description="Integration test event",
        status="published"
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    category = TicketCategory(
        event_id=event.id,
        name="General",
        price=1000,
        quantity=10
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return {
        "user": user,
        "venue": venue,
        "event": event,
        "category": category
    }


def test_booking_creates_tickets_and_notification(db, event_data):
    data = event_data
    system = AgentSystem(db)

    response = system.book_tickets(
        data["user"].id,
        data["event"].id,
        data["category"].id,
        2
    )

    assert response["performative"] == "AGREE"
    assert db.query(Booking).count() == 1
    assert db.query(Ticket).count() == 2
    assert db.query(Notification).count() == 1

    db.refresh(data["category"])
    assert data["category"].quantity == 8


def test_booking_prevents_overselling(db, event_data):
    data = event_data
    data["category"].quantity = 2
    db.commit()

    response = AgentSystem(db).book_tickets(
        data["user"].id,
        data["event"].id,
        data["category"].id,
        3
    )

    assert response["performative"] == "REFUSE"
    assert db.query(Booking).count() == 0


def test_booking_quantity_limit(db, event_data):
    data = event_data

    response = AgentSystem(db).book_tickets(
        data["user"].id,
        data["event"].id,
        data["category"].id,
        7
    )

    assert response["performative"] == "REFUSE"


def test_invalid_ticket_category(db, event_data):
    data = event_data

    response = AgentSystem(db).book_tickets(
        data["user"].id,
        data["event"].id,
        99999,
        1
    )

    assert response["performative"] == "REFUSE"


def test_ticket_scan_admits_only_once(db, event_data):
    data = event_data
    system = AgentSystem(db)

    booking = system.book_tickets(
        data["user"].id,
        data["event"].id,
        data["category"].id,
        1
    )

    code = booking["content"]["tickets"][0]["code"]

    first_scan = system.bus.communicate(
        sender="EventSphere",
        receiver="TicketAgent",
        performative="REQUEST",
        content={
            "action": "SCAN_TICKET",
            "code": code,
            "event_id": data["event"].id
        }
    )

    second_scan = system.bus.communicate(
        sender="EventSphere",
        receiver="TicketAgent",
        performative="REQUEST",
        content={
            "action": "SCAN_TICKET",
            "code": code,
            "event_id": data["event"].id
        }
    )

    assert first_scan["performative"] == "AGREE"
    assert second_scan["performative"] == "REFUSE"


def test_ticket_rejects_wrong_event(db, event_data):
    data = event_data
    system = AgentSystem(db)

    booking = system.book_tickets(
        data["user"].id,
        data["event"].id,
        data["category"].id,
        1
    )

    code = booking["content"]["tickets"][0]["code"]

    response = system.bus.communicate(
        sender="EventSphere",
        receiver="TicketAgent",
        performative="REQUEST",
        content={
            "action": "SCAN_TICKET",
            "code": code,
            "event_id": data["event"].id + 999
        }
    )

    assert response["performative"] == "REFUSE"


def test_waitlist_join(db, event_data):
    data = event_data
    system = AgentSystem(db)

    response = system.join_waitlist(
        data["user"].id,
        data["event"].id,
        data["category"].id
    )

    assert response["performative"] == "AGREE"
    assert db.query(Waitlist).count() == 1


def test_waitlist_prevents_duplicate_entries(db, event_data):
    data = event_data
    system = AgentSystem(db)

    first = system.join_waitlist(
        data["user"].id,
        data["event"].id,
        data["category"].id
    )

    second = system.join_waitlist(
        data["user"].id,
        data["event"].id,
        data["category"].id
    )

    assert first["performative"] == "AGREE"
    assert second["performative"] == "AGREE"
    assert first["content"]["waitlist_id"] == second["content"]["waitlist_id"]
    assert db.query(Waitlist).count() == 1


def test_waitlist_agent_expiry_sweep_releases_held_seat(db, event_data):
    data = event_data
    data["category"].quantity = 9
    entry = Waitlist(
        user_id=data["user"].id,
        event_id=data["event"].id,
        category_id=data["category"].id,
        status="offered",
        hold_until=datetime.utcnow() - timedelta(minutes=1)
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    response = AgentSystem(db).expire_waitlist_holds()

    db.refresh(entry)
    db.refresh(data["category"])
    assert response["performative"] == "INFORM"
    assert response["content"]["expired_count"] == 1
    assert entry.status == "expired"
    assert data["category"].quantity == 10


def test_venue_agent_detects_conflict(db, event_data):
    data = event_data
    system = AgentSystem(db)

    response = system.check_venue(
        data["venue"].id,
        data["event"].start_time,
        data["event"].end_time
    )

    assert response["performative"] == "REFUSE"


def test_venue_agent_accepts_available_venue(db, event_data):
    data = event_data
    system = AgentSystem(db)

    response = system.check_venue(
        data["venue"].id,
        data["event"].end_time + timedelta(days=1),
        data["event"].end_time + timedelta(days=1, hours=2)
    )

    assert response["performative"] == "AGREE"
    assert response["content"]["estimated_price"] == 1000


def test_agent_messages_are_logged(db, event_data):
    data = event_data
    system = AgentSystem(db)

    system.join_waitlist(
        data["user"].id,
        data["event"].id,
        data["category"].id
    )

    messages = db.query(AgentMessage).all()

    assert len(messages) >= 2
    assert any(message.receiver == "WaitlistAgent" for message in messages)
    assert any(message.sender == "WaitlistAgent" for message in messages)


def test_notification_agent_handles_broadcast_inform(db, event_data):
    data = event_data
    response = AgentSystem(db).notify(
        data["user"].id,
        "A required account notification."
    )

    assert response["performative"] == "AGREE"
    notification = db.query(Notification).one()
    assert notification.user_id == data["user"].id
    assert notification.message == "A required account notification."


def test_venue_agent_proposes_hire_alternatives(db, event_data):
    data = event_data
    response = AgentSystem(db).check_hire(
        data["venue"].id,
        data["event"].start_time,
        data["event"].end_time,
        guests=20
    )

    assert response["performative"] == "PROPOSE"
    assert response["content"]["reason"]
    assert response["content"]["alternatives"]
    assert response["content"]["alternatives"][0]["start_time"]


def test_venue_agent_ignores_hire_being_reviewed(db, event_data):
    data = event_data
    data["event"].status = "cancelled"
    hire = VenueHire(
        user_id=data["user"].id,
        venue_id=data["venue"].id,
        start_time=data["event"].start_time,
        end_time=data["event"].end_time,
        purpose="Review test",
        guests=10,
        price=1000,
        status="pending_admin"
    )
    db.add(hire)
    db.commit()
    db.refresh(hire)

    response = AgentSystem(db).check_venue(
        data["venue"].id,
        hire.start_time,
        hire.end_time,
        exclude_hire_id=hire.id
    )

    assert response["performative"] == "AGREE"


def test_event_cancellation_fully_refunds_and_invalidates_tickets(db, event_data):
    data = event_data
    system = AgentSystem(db)
    booking_response = system.book_tickets(
        data["user"].id,
        data["event"].id,
        data["category"].id,
        2
    )
    booking_id = booking_response["content"]["booking"]["booking_id"]

    response = system.cancel_event(data["event"].id)

    booking = db.get(Booking, booking_id)
    tickets = db.query(Ticket).filter(Ticket.booking_id == booking_id).all()
    db.refresh(data["category"])

    assert response["performative"] == "INFORM"
    assert booking.status == "cancelled"
    assert booking.refund_amount == booking.total
    assert data["category"].quantity == 10
    assert len(tickets) == 2
    assert all(ticket.status == "cancelled" for ticket in tickets)
    assert db.query(Notification).count() == 2
