# Infant Booking Feature

## Overview
The Galaxium Travels booking system now supports booking flights with infants (children under 2 years old). Infants can travel on a passenger's lap and do not require a separate seat.

## Features

### Backend Changes

#### 1. Database Model (`booking_system_backend/models.py`)
- Added `infant_count` column to the `Booking` table
- Default value: 0
- Type: Integer (non-nullable)

#### 2. API Schemas (`booking_system_backend/schemas.py`)
- **BookingRequest**: Added optional `infant_count` parameter (default: 0)
- **BookingOut**: Added `infant_count` field to booking response

#### 3. Booking Service (`booking_system_backend/services/booking.py`)
- Updated `book_flight()` function to accept `infant_count` parameter
- Added validation to ensure infant_count is not negative
- Infants don't consume seat inventory (they sit on passenger's lap)

#### 4. API Endpoints (`booking_system_backend/server.py`)
- Updated `/book` endpoint to accept infant_count in request body
- Updated MCP tool `book_flight` to support infant_count parameter

### Frontend Changes

#### 1. TypeScript Types (`booking_system_frontend/src/types/index.ts`)
- Added `infant_count` to `Booking` interface
- Added optional `infant_count` to `BookingRequest` interface

#### 2. Booking Modal (`booking_system_frontend/src/components/bookings/BookingModal.tsx`)
- Added infant selection UI with increment/decrement buttons
- Maximum of 4 infants per booking
- Visual feedback showing selected infant count
- Baby icon for better UX
- Note explaining that infants don't require separate seats

#### 3. Booking Card (`booking_system_frontend/src/components/bookings/BookingCard.tsx`)
- Displays infant count when viewing existing bookings
- Shows baby icon with count in a highlighted section
- Only displays when infant_count > 0

## Usage

### API Example

**Book a flight with 2 infants:**
```bash
POST /book
{
  "user_id": 1,
  "name": "John Doe",
  "flight_id": 5,
  "infant_count": 2
}
```

**Response:**
```json
{
  "booking_id": 123,
  "user_id": 1,
  "flight_id": 5,
  "status": "booked",
  "booking_time": "2026-05-07T05:00:00",
  "infant_count": 2
}
```

### Frontend Usage

1. **Booking a Flight:**
   - Click "Book Now" on any flight
   - In the booking modal, use the +/- buttons to select number of infants
   - Maximum 4 infants per booking
   - Infants are free (no additional charge)
   - Click "Confirm Booking"

2. **Viewing Bookings:**
   - Navigate to "My Bookings"
   - Bookings with infants will show a purple badge with baby icon
   - Example: "2 infants traveling"

## Database Migration

If you have an existing database, run the migration script:

```bash
cd booking_system_backend
python migrate_add_infant_count.py
```

This will add the `infant_count` column to existing bookings with a default value of 0.

## Business Rules

1. **Infant Definition**: Children under 2 years old
2. **Seating**: Infants sit on passenger's lap (no separate seat required)
3. **Pricing**: No additional charge for infants
4. **Limit**: Maximum 4 infants per booking
5. **Validation**: Infant count cannot be negative

## Technical Notes

- Infants do NOT decrement the `seats_available` count
- The feature is backward compatible (infant_count defaults to 0)
- All existing bookings will have infant_count = 0 after migration
- The UI gracefully handles bookings with 0 infants (no badge shown)

## Testing

To test the feature:

1. Start the backend server:
   ```bash
   cd booking_system_backend
   python server.py
   ```

2. Start the frontend:
   ```bash
   cd booking_system_frontend
   npm run dev
   ```

3. Test scenarios:
   - Book a flight without infants (should work as before)
   - Book a flight with 1 infant
   - Book a flight with multiple infants (up to 4)
   - Try to add more than 4 infants (button should be disabled)
   - View bookings with infants in "My Bookings" page
   - Cancel a booking with infants

## Future Enhancements

Potential improvements for future versions:
- Add age verification for infants
- Support for children (2-12 years) with separate seats
- Infant-specific pricing tiers
- Limit infants per adult passenger
- Special meal requests for infants
- Infant equipment (stroller, car seat) booking

---

**Made with Bob** 🤖