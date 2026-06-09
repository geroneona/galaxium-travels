# Infant Discount System Documentation

## Overview
The Galaxium Travels booking system now includes a comprehensive discount system for infant bookings, with all discount calculations stored in the database.

## Pricing Logic

### Infant Discount Rules
- **1 infant**: Sits on passenger's lap, **NO additional charge** (Total = Original Price)
- **2+ infants**: First infant sits on lap (free), additional infants get **25% discount each**

### Calculation Formula
```
Additional Infants = max(0, infant_count - 1)
Discount Amount = Original Price × 0.25 × Additional Infants
Total Price = Original Price + Discount Amount
```

### Examples

**Example 1: 1 Infant**
- Original Price: $950,000
- Additional Infants: 1 - 1 = 0
- Discount: $0
- **Total: $950,000** (no additional charge)

**Example 2: 2 Infants**
- Original Price: $500,000
- Additional Infants: 2 - 1 = 1
- Discount: $500,000 × 0.25 × 1 = $125,000
- **Total: $625,000**

**Example 3: 3 Infants**
- Original Price: $5,000,000
- Additional Infants: 3 - 1 = 2
- Discount: $5,000,000 × 0.25 × 2 = $2,500,000
- **Total: $7,500,000**

## Database Schema

### Discounts Table
```sql
CREATE TABLE discounts (
    discount_id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    infant_count INTEGER NOT NULL DEFAULT 0,
    original_price INTEGER NOT NULL,
    discounted_price_per_infant INTEGER NOT NULL,
    applied_discounted_price_per_infant_count INTEGER NOT NULL,
    flight_id INTEGER NOT NULL,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    departure_time TEXT NOT NULL,
    arrival_time TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
);
```

### Fields Explanation
- `discount_id`: Unique identifier for the discount record
- `booking_id`: Links to the booking that has infants
- `infant_count`: Number of infants in the booking
- `original_price`: Base flight price (before any infant charges)
- `discounted_price_per_infant`: 25% of original price (discount rate per infant)
- `applied_discounted_price_per_infant_count`: Final total price with infant charges
- Flight & User details: Denormalized for easy querying

## Backend Implementation

### Models (`booking_system_backend/models.py`)
```python
class Discount(Base):
    __tablename__ = 'discounts'
    discount_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey('bookings.booking_id'), nullable=False)
    infant_count = Column(Integer, nullable=False, default=0)
    original_price = Column(Integer, nullable=False)
    discounted_price_per_infant = Column(Integer, nullable=False)
    applied_discounted_price_per_infant_count = Column(Integer, nullable=False)
    # ... other fields
```

### Seed Data (`booking_system_backend/seed.py`)
Discount records are automatically created for all bookings with infants:
```python
# Calculate total price with infant discount logic
additional_infants = max(0, booking.infant_count - 1)
discount_amount = int(flight.price * 0.25 * additional_infants)
total_price = flight.price + discount_amount
```

### API Endpoints (`booking_system_backend/server.py`)

#### Get All Discounts
```http
GET /discounts
Response: DiscountOut[]
```

#### Get Discount by Booking ID
```http
GET /discounts/booking/{booking_id}
Response: DiscountOut | null
```

#### Get Discounts by User Email
```http
GET /discounts/user/{email}
Response: DiscountOut[]
```

### Service Layer (`booking_system_backend/services/discount.py`)
```python
def get_discount_by_booking_id(db: Session, booking_id: int) -> DiscountOut | None
def get_all_discounts(db: Session) -> list[DiscountOut]
def get_discounts_by_user_email(db: Session, email: str) -> list[DiscountOut]
```

## Frontend Implementation

### TypeScript Types (`booking_system_frontend/src/types/index.ts`)
```typescript
export interface Discount {
  discount_id: number;
  booking_id: number;
  infant_count: number;
  original_price: number;
  discounted_price_per_infant: number;
  applied_discounted_price_per_infant_count: number;
  flight_id: number;
  origin: string;
  destination: string;
  departure_time: string;
  arrival_time: string;
  name: string;
  email: string;
}
```

### API Service (`booking_system_frontend/src/services/api.ts`)
```typescript
export const getAllDiscounts = async (): Promise<Discount[]>
export const getDiscountByBooking = async (bookingId: number): Promise<Discount | null>
export const getDiscountsByUserEmail = async (email: string): Promise<Discount[]>
```

### Booking Modal (`booking_system_frontend/src/components/bookings/BookingModal.tsx`)
The booking modal calculates and displays the total price in real-time:
```typescript
const calculateTotalPrice = () => {
  const basePrice = flight.price;
  if (infantCount > 1) {
    const infantDiscount = basePrice * 0.25 * (infantCount - 1);
    return basePrice + infantDiscount;
  }
  return basePrice; // No charge for single infant
};
```

## Usage Examples

### Backend: Query Discounts
```python
from db import SessionLocal
from services.discount import get_discounts_by_user_email

db = SessionLocal()
discounts = get_discounts_by_user_email(db, "alice@example.com")
for discount in discounts:
    print(f"Flight: {discount.origin} → {discount.destination}")
    print(f"Infants: {discount.infant_count}")
    print(f"Total: ${discount.applied_discounted_price_per_infant_count:,}")
db.close()
```

### Frontend: Fetch User Discounts
```typescript
import { getDiscountsByUserEmail } from './services/api';

const discounts = await getDiscountsByUserEmail(user.email);
discounts.forEach(discount => {
  console.log(`Booking ${discount.booking_id}: ${discount.infant_count} infants`);
  console.log(`Total: $${discount.applied_discounted_price_per_infant_count.toLocaleString()}`);
});
```

## Testing

### Verify Discount Calculations
```bash
cd booking_system_backend
python -c "
import sqlite3
conn = sqlite3.connect('booking.db')
cursor = conn.cursor()
cursor.execute('SELECT booking_id, infant_count, original_price, applied_discounted_price_per_infant_count FROM discounts LIMIT 5')
for row in cursor.fetchall():
    print(f'Booking {row[0]}: {row[1]} infants, Original: ${row[2]:,}, Total: ${row[3]:,}')
conn.close()
"
```

### Run Backend Server
```bash
cd booking_system_backend
python server.py
```

### Test API Endpoints
```bash
# Get all discounts
curl http://localhost:8080/discounts

# Get discount for booking ID 1
curl http://localhost:8080/discounts/booking/1

# Get discounts for user
curl http://localhost:8080/discounts/user/alice@example.com
```

## Business Rules Summary

1. **Infant Definition**: Children under 2 years old
2. **First Infant**: Always free (sits on passenger's lap)
3. **Additional Infants**: 25% of base price per infant
4. **No Seat Required**: Infants don't consume seat inventory
5. **Maximum Infants**: Up to 8 infants per booking (configurable in UI)
6. **Discount Storage**: All calculations stored in database for reporting and auditing

## Benefits of Database-Stored Discounts

✅ **Audit Trail**: Complete history of all discount calculations
✅ **Reporting**: Easy to generate discount reports and analytics
✅ **Consistency**: Single source of truth for pricing
✅ **Performance**: Pre-calculated totals for fast queries
✅ **Flexibility**: Can adjust discount rules without recalculating historical data

---

**Made with Bob** 🤖