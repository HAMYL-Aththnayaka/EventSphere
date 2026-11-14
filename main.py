from fastapi import FastAPI

app = FastAPI(
    title="EventSphere",
    description="Agent-Based Venue Booking and Ticketing System",
    version="1.0.0"
)

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