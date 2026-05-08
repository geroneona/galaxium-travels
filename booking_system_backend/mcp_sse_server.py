"""
MCP SSE Server for IBM Agentic App Studio
This is a SEPARATE server from server.py (port 8080).
This MCP server will run on port 8000 and provide tools to IBM Agentic App Studio.

Run this with: python mcp_sse_server.py
Then expose it with ngrok: ngrok http 8000
Use the ngrok URL in IBM Agentic App Studio.
"""

from fastmcp import FastMCP
from typing import Union, Dict, Any
import requests
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


@mcp.tool()
def book_flight_remote(
    user_name: str,
    user_email: str,
    origin: str,
    destination: str,
    infant_count: int = 0,
    base_url: str = "https://brownnose-igloo-ideally.ngrok-free.dev"
) -> Dict[str, Any]:
    """Book a flight on a remote API server with comprehensive booking details.
    
    This tool handles the complete booking workflow:
    1. Checks if user exists on the remote server
    2. Registers user if needed
    3. Lists and filters flights by origin/destination
    4. Books the flight with optional infant passengers
    5. Retrieves discount details if applicable
    
    Args:
        user_name: Name of the passenger
        user_email: Email address of the passenger
        origin: Departure location (e.g., "Earth", "Mars")
        destination: Arrival location (e.g., "Mars", "Jupiter")
        infant_count: Number of infants (default: 0, infants get 75% discount)
        base_url: Remote API base URL (default: ngrok tunnel URL)
    
    Returns:
        Comprehensive booking summary including:
        - User information
        - Flight details
        - Booking confirmation
        - Discount information (if applicable)
        - Total cost breakdown
    
    Raises:
        Exception: If any step in the booking process fails
    """
    try:
        # Step 1: Check if user exists
        print(f"[1/5] Checking if user '{user_name}' exists on remote server...")
        user_response = requests.get(
            f"{base_url}/user",
            params={"name": user_name, "email": user_email},
            timeout=10
        )
        
        user_data = None
        if user_response.status_code == 200:
            response_json = user_response.json()
            # Check if it's an error response
            if not response_json.get('success') == False and 'error' not in response_json:
                user_data = response_json
                print(f"✓ User found: ID {user_data.get('user_id')}")
        
        # Step 2: Register user if not found
        if not user_data:
            print(f"[2/5] Registering new user '{user_name}'...")
            register_response = requests.post(
                f"{base_url}/register",
                json={"name": user_name, "email": user_email},
                timeout=10
            )
            
            if register_response.status_code != 200:
                raise Exception(f"Failed to register user: {register_response.status_code} - {register_response.text}")
            
            user_data = register_response.json()
            if user_data.get('success') == False or 'error' in user_data:
                raise Exception(f"User registration failed: {user_data.get('error', 'Unknown error')}")
            
            print(f"✓ User registered: ID {user_data.get('user_id')}")
        else:
            print(f"[2/5] User already exists, skipping registration")
        
        user_id = user_data.get('user_id') or user_data.get('id')
        if not user_id:
            raise Exception("Failed to get user_id from response")
        
        # Step 3: List and filter flights
        print(f"[3/5] Searching for flights from {origin} to {destination}...")
        flights_response = requests.get(f"{base_url}/flights", timeout=10)
        
        if flights_response.status_code != 200:
            raise Exception(f"Failed to list flights: {flights_response.status_code}")
        
        all_flights = flights_response.json()
        matching_flights = [
            f for f in all_flights 
            if f.get('origin') == origin and f.get('destination') == destination
        ]
        
        if not matching_flights:
            raise Exception(f"No flights found from {origin} to {destination}")
        
        # Use the first matching flight
        flight = matching_flights[0]
        flight_id = flight.get('flight_id') or flight.get('id')
        print(f"✓ Found flight ID {flight_id}: {origin} → {destination}, ${flight.get('price')}")
        
        # Step 4: Book the flight
        print(f"[4/5] Booking flight {flight_id} for {user_name} with {infant_count} infant(s)...")
        booking_response = requests.post(
            f"{base_url}/book",
            json={
                "user_id": user_id,
                "name": user_name,
                "flight_id": flight_id,
                "infant_count": infant_count
            },
            timeout=10
        )
        
        if booking_response.status_code != 200:
            raise Exception(f"Booking failed: {booking_response.status_code} - {booking_response.text}")
        
        booking_data = booking_response.json()
        if booking_data.get('success') == False or 'error' in booking_data:
            raise Exception(f"Booking failed: {booking_data.get('error', 'Unknown error')}")
        
        booking_id = booking_data.get('booking_id') or booking_data.get('id')
        print(f"✓ Booking successful: ID {booking_id}")
        
        # Step 5: Get discount details
        discount_data = None
        if infant_count > 0:
            print(f"[5/5] Retrieving discount details for booking {booking_id}...")
            discount_response = requests.get(
                f"{base_url}/discounts/booking/{booking_id}",
                timeout=10
            )
            
            if discount_response.status_code == 200:
                discount_data = discount_response.json()
                if discount_data:
                    print(f"✓ Discount applied: ${discount_data.get('applied_discounted_price_per_infant_count')} total")
                else:
                    print("ℹ No discount information available")
            else:
                print(f"⚠ Could not retrieve discount details: {discount_response.status_code}")
        else:
            print(f"[5/5] No infants, skipping discount check")
        
        # Build comprehensive summary
        base_price = flight.get('price', 0)
        total_cost = base_price
        
        if discount_data:
            total_cost = discount_data.get('applied_discounted_price_per_infant_count', base_price)
            savings = (base_price * infant_count) - total_cost
        else:
            savings = 0
        
        summary = {
            "success": True,
            "booking_id": booking_id,
            "user": {
                "user_id": user_id,
                "name": user_name,
                "email": user_email
            },
            "flight": {
                "flight_id": flight_id,
                "origin": flight.get('origin'),
                "destination": flight.get('destination'),
                "departure_time": flight.get('departure_time'),
                "arrival_time": flight.get('arrival_time'),
                "base_price": base_price,
                "seats_available": flight.get('seats_available')
            },
            "booking": {
                "booking_id": booking_id,
                "status": booking_data.get('status'),
                "booking_time": booking_data.get('booking_time'),
                "infant_count": infant_count
            },
            "pricing": {
                "base_price": base_price,
                "infant_count": infant_count,
                "discount_applied": discount_data is not None,
                "total_cost": total_cost,
                "savings": savings
            }
        }
        
        if discount_data:
            summary["discount"] = {
                "discount_id": discount_data.get('discount_id'),
                "original_price": discount_data.get('original_price'),
                "discounted_price_per_infant": discount_data.get('discounted_price_per_infant'),
                "total_discount_price": discount_data.get('applied_discounted_price_per_infant_count'),
                "discount_percentage": 75
            }
        
        print("\n✅ Booking completed successfully!")
        return summary
        
    except requests.exceptions.Timeout:
        raise Exception(f"Request timeout: Could not connect to {base_url}")
    except requests.exceptions.ConnectionError:
        raise Exception(f"Connection error: Could not reach {base_url}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"HTTP request failed: {str(e)}")
    except Exception as e:
        raise Exception(f"Booking failed: {str(e)}")


if __name__ == "__main__":
    print("=" * 80)
    print("MCP SSE Server for IBM Agentic App Studio")
    print("=" * 80)
    print("This is a SEPARATE server from your booking API (port 8080)")
    print("This MCP server will run on port 8000")
    print()
    print("STEPS TO USE:")
    print("1. Run this server: python mcp_sse_server.py")
    print("2. In another terminal, expose it: ngrok http 8000")
    print("3. Copy the ngrok URL (e.g., https://abc123.ngrok-free.dev)")
    print("4. In IBM Agentic App Studio, use: https://abc123.ngrok-free.dev/sse")
    print("=" * 80)
    
    # Run the MCP server with SSE transport
    mcp.run(transport="sse")

# Made with Bob