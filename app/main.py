
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import booking, admin, hire, waitlist, scanner, dashboard


# Paths for frontend files
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


app = FastAPI(
    title="EventSphere",
    description="Agent-Based Venue Booking and Ticketing System",
    version="1.0.0"
)

# Serve CSS, JavaScript and other static files
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)

# Register existing API routers
app.include_router(admin.router)
app.include_router(booking.router)
app.include_router(hire.router)
app.include_router(waitlist.router)
app.include_router(scanner.router)
app.include_router(dashboard.router)


# Public homepage
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "page_title": "Discover Events | EventSphere"
        }
    )


# Health/test endpoint
@app.get("/test")
def test():
    return {
        "Message": "EventSphere is working successfully!"
    }
