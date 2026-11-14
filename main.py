from fastapi import FastAPI

from app.routers import booking
from app.routers import admin
from app.routers import hire, waitlist
from app.routers import scanner, dashboard






app = FastAPI(
    title="EventSphere",
    description="Agent-Based Venue Booking and Ticketing System",
    version="1.0.0"
)

# router added
app.include_router(admin.router)
app.include_router(booking.router)
app.include_router(hire.router)
app.include_router(waitlist.router)
app.include_router(scanner.router)
app.include_router(dashboard.router)


#Home page
@app.get("/")
def home():
    return{
        "Message":"Welcome to EventSphere",
        "status":"Application is running"
    }

#Test page
@app.get("/test")
def test():
    return{
        "Message":"EventSphere is working successfully !"
    }


