from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(100), unique=True)
    password = Column(String(255))
    role = Column(String(20), default="attendee")


class Venue(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    location = Column(String(200))
    capacity = Column(Integer)
    description = Column(Text)
    image = Column(String(255))
    hourly_rate = Column(Float)
    private_hire = Column(Boolean, default=True)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    title = Column(String(150))
    category = Column(String(100))
    venue_id = Column(Integer, ForeignKey("venues.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    description = Column(Text)
    status = Column(String(20), default="draft")


class TicketCategory(Base):
    __tablename__ = "ticket_categories"

    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"))
    name = Column(String(100))
    price = Column(Float)
    quantity = Column(Integer)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_id = Column(Integer, ForeignKey("events.id"))
    category_id = Column(Integer, ForeignKey("ticket_categories.id"))
    quantity = Column(Integer)
    total = Column(Float)
    payment_reference = Column(String(100))
    status = Column(String(30), default="confirmed")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    event_id = Column(Integer, ForeignKey("events.id"))
    code = Column(String(150), unique=True)
    status = Column(String(20), default="valid")
    checked_in = Column(Boolean, default=False)


class VenueHire(Base):
    __tablename__ = "venue_hire"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    venue_id = Column(Integer, ForeignKey("venues.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    purpose = Column(String(200))
    guests = Column(Integer)
    price = Column(Float)
    status = Column(String(30), default="pending")


class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    event_id = Column(Integer)
    category_id = Column(Integer)
    status = Column(String(30), default="waiting")
    hold_until = Column(DateTime, nullable=True)


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(String(100))
    sender = Column(String(50))
    receiver = Column(String(50))
    performative = Column(String(20))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    message = Column(String(300))
    created_at = Column(DateTime, default=datetime.utcnow)