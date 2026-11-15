
import asyncio
import logging
import os
import secrets
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.csrf import CSRFMiddleware
from app.database import SessionLocal, initialize_database
from app.init import create_admin_from_environment
from app.routers import (
    booking,
    admin,
    hire,
    waitlist,
    scanner,
    dashboard,
    events,
)
from app import auth
from app.auth import require_roles


BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


async def waitlist_expiry_scheduler():
    while True:
        db = SessionLocal()
        try:
            from app.agents.agent_system import AgentSystem
            AgentSystem(db).expire_waitlist_holds()
        except Exception:
            logger.exception("Waitlist expiry sweep failed.")
        finally:
            db.close()
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app):
    initialize_database()
    create_admin_from_environment()
    scheduler = asyncio.create_task(waitlist_expiry_scheduler())
    try:
        yield
    finally:
        scheduler.cancel()
        try:
            await scheduler
        except asyncio.CancelledError:
            pass


if os.getenv("APP_ENV", "development").lower() == "production" and not os.getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY must be configured in production.")

SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)

app = FastAPI(
    title="EventSphere",
    description="Agent-Based Venue Booking and Ticketing System",
    version="1.0.0",
    lifespan=lifespan,
)


# SESSION CONFIGURATION
# SessionMiddleware wraps CSRF middleware so the session is available there.
app.add_middleware(CSRFMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="eventsphere_session",
    same_site="lax",
    https_only=os.getenv(
        "HTTPS_ONLY",
        "true" if os.getenv("APP_ENV", "development").lower() == "production" else "false"
    ).lower() == "true",
)


# STATIC FILES
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)


# BACKEND API ROUTERS
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(booking.router)
app.include_router(hire.router)
app.include_router(waitlist.router)
app.include_router(scanner.router)
app.include_router(dashboard.router)
app.include_router(events.router)


# FRONTEND PAGE ROUTES
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "page_title": "EventSphere | Discover. Experience. Remember."
        },
    )


@app.get("/events-page")
async def events_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="events.html",
        context={
            "page_title": "Discover Events | EventSphere"
        },
    )


@app.get("/my-bookings")
async def bookings_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="bookings.html",
        context={
            "page_title": "My Bookings | EventSphere"
        },
    )


@app.get("/venue-hire")
async def venue_hire_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="hire.html",
        context={
            "page_title": "Venue Hire | EventSphere"
        },
    )


@app.get(
    "/dashboard",
    dependencies=[Depends(require_roles("admin"))]
)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "page_title": "Management Dashboard | EventSphere"
        },
    )


@app.get(
    "/scanner-page",
    dependencies=[Depends(require_roles("staff", "admin"))]
)
async def scanner_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="scanner.html",
        context={
            "page_title": "Ticket Scanner | EventSphere"
        },
    )


# CONNECTION TEST
@app.get("/test")
def test():
    return {
        "Message": "EventSphere is working successfully!"
    }
