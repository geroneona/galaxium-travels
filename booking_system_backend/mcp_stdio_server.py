"""
MCP Stdio Server for IBM Agent Studio
This server runs independently and communicates via stdio protocol.
Run this with: python mcp_stdio_server.py
"""

from fastmcp import FastMCP
from typing import Union
from db import SessionLocal, init_db
from services import flight, user, booking, discount
from schemas import FlightOut, BookingOut, UserOut, ErrorResponse, DiscountOut

# Initialize database
init_db()

# Create MCP server
mcp = FastMCP("Galaxium Booking System")


@mcp.tool()
def list_flights() -> list[FlightOut]:
    """List all available flights.
    Returns a list of flights with origin, destination, times, price, and seats available."""
    db = SessionLocal()
    try:
        return flight.list_flights(db)
    finally:
        db.close()


@mcp.tool()
def book_flight(user_id: int, name: str, flight_id: int, infant_count: int = 0) -> BookingOut:
    """Book a seat on a specific flight for a user with optional infants.
    Requires user_id, name, and flight_id. Optionally specify infant_count (default 0).
    Decrements available seats if successful. Infants don't require separate seats.
    Returns booking details or raises an error if booking is not possible."""
    db = SessionLocal()
    try:
        result = booking.book_flight(db, user_id, name, flight_id, infant_count)
        if isinstance(result, ErrorResponse):
            raise Exception(result.details or result.error)
        return result
    finally:
        db.close()


@mcp.tool()
def get_bookings(user_id: int) -> list[BookingOut]:
    """Retrieve all bookings for a specific user by user_id.
    Returns a list of booking details for the user."""
    db = SessionLocal()
    try:
        return booking.get_bookings(db, user_id)
    finally:
        db.close()


@mcp.tool()
def cancel_booking(booking_id: int) -> BookingOut:
    """Cancel an existing booking by its booking_id.
    Increments available seats for the flight if successful.
    Returns updated booking details or raises an error if already cancelled or not found."""
    db = SessionLocal()
    try:
        result = booking.cancel_booking(db, booking_id)
        if isinstance(result, ErrorResponse):
            raise Exception(result.details or result.error)
        return result
    finally:
        db.close()


@mcp.tool()
def register_user(name: str, email: str) -> UserOut:
    """Register a new user with a name and unique email.
    Returns the created user's details or raises an error if the email is already registered."""
    db = SessionLocal()
    try:
        result = user.register_user(db, name, email)
        if isinstance(result, ErrorResponse):
            raise Exception(result.details or result.error)
        return result
    finally:
        db.close()


@mcp.tool()
def get_user_id(name: str, email: str) -> UserOut:
    """Retrieve a user's information, including user_id, by providing both name and email.
    Returns user details or raises an error if not found."""
    db = SessionLocal()
    try:
        result = user.get_user(db, name, email)
        if isinstance(result, ErrorResponse):
            raise Exception(result.details or result.error)
        return result
    finally:
        db.close()


@mcp.tool()
def get_discount_by_booking(booking_id: int) -> Union[DiscountOut, None]:
    """Get discount information for a specific booking.
    Returns discount details including infant pricing if applicable, or None if no discount."""
    db = SessionLocal()
    try:
        return discount.get_discount_by_booking_id(db, booking_id)
    finally:
        db.close()


if __name__ == "__main__":
    # Run the MCP server in stdio mode
    mcp.run()

# Made with Bob
