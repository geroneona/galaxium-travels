from db import SessionLocal
from services.booking import book_flight
from models import Discount

db = SessionLocal()

# Test booking with 2 infants
print("Testing booking with 2 infants...")
result = book_flight(db, 1, 'Alice', 1, 2)

if hasattr(result, 'booking_id'):
    print(f"✓ Booking created: ID {result.booking_id}")
    
    # Check if discount was created
    discount = db.query(Discount).filter(Discount.booking_id == result.booking_id).first()
    if discount:
        print(f"✓ Discount record created!")
        print(f"  - Infant count: {discount.infant_count}")
        print(f"  - Original price: ${discount.original_price:,}")
        print(f"  - Discount per infant: ${discount.discounted_price_per_infant:,}")
        print(f"  - Total price: ${discount.applied_discounted_price_per_infant_count:,}")
    else:
        print("✗ No discount record found!")
else:
    print(f"✗ Booking failed: {result.error}")

db.close()

# Made with Bob
