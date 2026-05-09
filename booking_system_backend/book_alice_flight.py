import requests
import time
import json
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Base URL for the API
BASE_URL = "http://localhost:8080"

def wait_for_server(max_attempts=10):
    """Wait for server to be ready"""
    print("Waiting for server to start...")
    for i in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/flights", timeout=2)
            if response.status_code == 200:
                print("[OK] Server is ready!")
                return True
        except requests.exceptions.RequestException:
            time.sleep(1)
    print("[ERROR] Server failed to start")
    return False

def check_or_create_user(name, email):
    """Check if user exists, create if not"""
    print(f"\n1. Checking if user '{name}' exists...")
    
    # Try to get user by name and email
    try:
        response = requests.get(f"{BASE_URL}/user", params={"name": name, "email": email})
        if response.status_code == 200:
            user = response.json()
            # Check if it's an error response
            if user.get('success') == False or 'error' in user:
                print(f"User not found: {user.get('error', 'Unknown error')}")
            else:
                print(f"[OK] User found: {user}")
                return user
    except requests.exceptions.RequestException as e:
        print(f"User not found, will create new user")
    
    # Create new user
    print(f"\n2. Registering new user '{name}'...")
    user_data = {
        "name": name,
        "email": email
    }
    response = requests.post(f"{BASE_URL}/register", json=user_data)
    if response.status_code == 200:
        user = response.json()
        print(f"[OK] User created: {user}")
        return user
    else:
        print(f"[ERROR] Failed to create user: {response.status_code} - {response.text}")
        return None

def get_earth_to_mars_flights():
    """Get all flights from Earth to Mars"""
    print("\n3. Listing available flights from Earth to Mars...")
    
    response = requests.get(f"{BASE_URL}/flights")
    if response.status_code == 200:
        all_flights = response.json()
        earth_to_mars = [f for f in all_flights if f.get('origin') == 'Earth' and f.get('destination') == 'Mars']
        
        if earth_to_mars:
            print(f"[OK] Found {len(earth_to_mars)} flight(s) from Earth to Mars:")
            for flight in earth_to_mars:
                # Use .get() to safely access keys
                flight_id = flight.get('id') or flight.get('flight_id')
                print(f"  - Flight ID: {flight_id}")
                print(f"    Origin: {flight.get('origin')} -> Destination: {flight.get('destination')}")
                print(f"    Departure: {flight.get('departure_time')}")
                print(f"    Price: ${flight.get('price')}")
                print()
            return earth_to_mars
        else:
            print("[ERROR] No flights found from Earth to Mars")
            return []
    else:
        print(f"[ERROR] Failed to get flights: {response.status_code}")
        return []

def book_flight(user_id, name, flight_id, infant_count):
    """Book a flight with infants"""
    print(f"\n4. Booking flight {flight_id} for {name} with {infant_count} infant(s)...")
    
    booking_data = {
        "user_id": user_id,
        "name": name,
        "flight_id": flight_id,
        "infant_count": infant_count
    }
    
    response = requests.post(f"{BASE_URL}/book", json=booking_data)
    if response.status_code == 200:
        booking = response.json()
        booking_id = booking.get('booking_id') or booking.get('id')
        print(f"[OK] Booking successful!")
        print(f"  Booking ID: {booking_id}")
        print(f"  Status: {booking.get('status')}")
        print(f"  Infant Count: {booking.get('infant_count', 0)}")
        return booking
    else:
        print(f"[ERROR] Booking failed: {response.status_code} - {response.text}")
        return None

def get_discount_details(booking_id):
    """Get discount details for a booking"""
    print(f"\n5. Checking discount details for booking {booking_id}...")
    
    response = requests.get(f"{BASE_URL}/discounts/booking/{booking_id}")
    if response.status_code == 200:
        discount_data = response.json()
        
        # Handle both single discount object and list of discounts
        if discount_data is None:
            print("  No discounts applied to this booking")
            return []
        
        # Convert single discount to list for consistent handling
        if isinstance(discount_data, dict):
            discounts = [discount_data]
        else:
            discounts = discount_data
        
        if discounts:
            print(f"[OK] Discount(s) applied:")
            for discount in discounts:
                discount_id = discount.get('discount_id') or discount.get('id')
                print(f"  - Discount ID: {discount_id}")
                print(f"    Infant Count: {discount.get('infant_count')}")
                print(f"    Original Price: ${discount.get('original_price')}")
                print(f"    Discounted Price per Infant: ${discount.get('discounted_price_per_infant')}")
                print(f"    Total Applied Discount Price: ${discount.get('applied_discounted_price_per_infant_count')}")
            return discounts
        else:
            print("  No discounts applied to this booking")
            return []
    else:
        print(f"[ERROR] Failed to get discount details: {response.status_code}")
        return []

def print_summary(flight, booking, discounts):
    """Print a summary of the booking"""
    print("\n" + "="*70)
    print("BOOKING SUMMARY")
    print("="*70)
    
    flight_id = flight.get('flight_id') or flight.get('id')
    flight_price = flight.get('price', 0)
    booking_id = booking.get('booking_id') or booking.get('id')
    
    print("\n[FLIGHT DETAILS]")
    print(f"  Flight ID: {flight_id}")
    print(f"  Route: {flight.get('origin')} -> {flight.get('destination')}")
    print(f"  Departure: {flight.get('departure_time')}")
    print(f"  Base Price per Adult: ${flight_price:,}")
    
    print("\n[BOOKING CONFIRMATION]")
    print(f"  Booking ID: {booking_id}")
    print(f"  Passenger: {booking.get('name', 'N/A')}")
    print(f"  Status: {booking.get('status')}")
    print(f"  Infant Count: {booking.get('infant_count', 0)}")
    print(f"  Booking Time: {booking.get('booking_time', 'N/A')}")
    
    if discounts:
        print("\n[INFANT DISCOUNT DETAILS]")
        total_discount_price = 0
        for discount in discounts:
            infant_count = discount.get('infant_count', 0)
            original_price = discount.get('original_price', 0)
            discounted_price = discount.get('discounted_price_per_infant', 0)
            total_discount_price = discount.get('applied_discounted_price_per_infant_count', 0)
            
            print(f"  Infant Count: {infant_count}")
            print(f"  Original Adult Price: ${original_price:,}")
            print(f"  Discounted Price per Infant (75% off): ${discounted_price:,}")
            print(f"  Total Price for {infant_count} Infants: ${total_discount_price:,}")
            
            savings_per_infant = original_price - discounted_price
            total_savings = savings_per_infant * infant_count
            print(f"\n  Savings per Infant: ${savings_per_infant:,} (75% discount)")
            print(f"  Total Savings: ${total_savings:,}")
            
        print(f"\n  TOTAL COST: ${total_discount_price:,}")
    else:
        print("\n[DISCOUNTS] None applied")
        print(f"  TOTAL COST: ${flight_price:,}")
    
    print("\n" + "="*70)

def main():
    # Wait for server to be ready
    if not wait_for_server():
        print("Server is not responding. Please start it manually.")
        return
    
    # Step 1 & 2: Check/Create user
    user = check_or_create_user("Alice", "alice@email.com")
    if not user:
        print("Failed to get or create user. Exiting.")
        return
    
    # Step 3: Get flights
    flights = get_earth_to_mars_flights()
    if not flights:
        print("No flights available. Exiting.")
        return
    
    # Use the first available flight
    flight = flights[0]
    flight_id = flight.get('id') or flight.get('flight_id')
    user_id = user.get('id') or user.get('user_id')
    
    # Step 4: Book flight
    booking = book_flight(user_id, user['name'], flight_id, 3)
    if not booking:
        print("Booking failed. Exiting.")
        return
    
    # Step 5: Get discount details
    booking_id = booking.get('booking_id') or booking.get('id')
    discounts = get_discount_details(booking_id)
    
    # Step 6: Print summary
    print_summary(flight, booking, discounts)

if __name__ == "__main__":
    main()

# Made with Bob
