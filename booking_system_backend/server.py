from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Union
from db import SessionLocal, init_db, get_db
from seed import seed
from services import flight, user, booking
from schemas import FlightOut, BookingOut, UserOut, ErrorResponse, BookingRequest, UserRegistration


# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    seed()
    yield
    # Shutdown (nothing to do)


# ==================== FASTAPI APP (REST + Swagger UI) ====================

app = FastAPI(
    title="Galaxium Booking System",
    description="API for booking interplanetary flights. Swagger UI available at /docs",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "OK"}


@app.get("/flights", response_model=list[FlightOut], tags=["Flights"])
def get_flights(db: Session = Depends(get_db)):
    """List all available flights with origin, destination, times, price, and seats available."""
    return flight.list_flights(db)


@app.post("/book", response_model=Union[BookingOut, ErrorResponse], tags=["Bookings"])
def book_flight_endpoint(request: BookingRequest, db: Session = Depends(get_db)):
    """Book a seat on a specific flight for a user.

    Requires user_id, name, and flight_id. Decrements available seats if successful.
    """
    return booking.book_flight(db, request.user_id, request.name, request.flight_id)


@app.get("/bookings/{user_id}", response_model=list[BookingOut], tags=["Bookings"])
def get_user_bookings(user_id: int, db: Session = Depends(get_db)):
    """Retrieve all bookings for a specific user by user_id."""
    return booking.get_bookings(db, user_id)


@app.post("/cancel/{booking_id}", response_model=Union[BookingOut, ErrorResponse], tags=["Bookings"])
def cancel_booking_endpoint(booking_id: int, db: Session = Depends(get_db)):
    """Cancel an existing booking by its booking_id.

    Increments available seats for the flight if successful.
    """
    return booking.cancel_booking(db, booking_id)


@app.post("/register", response_model=Union[UserOut, ErrorResponse], tags=["Users"])
def register_user_endpoint(request: UserRegistration, db: Session = Depends(get_db)):
    """Register a new user with a name and unique email."""
    return user.register_user(db, request.name, request.email)


@app.get("/user", response_model=Union[UserOut, ErrorResponse], tags=["Users"])
def get_user_endpoint(name: str, email: str, db: Session = Depends(get_db)):
    """Retrieve a user's information by providing both name and email."""
    return user.get_user(db, name, email)


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
