// API Data Models matching backend schemas

export interface Flight {
  flight_id: number;
  origin: string;
  destination: string;
  departure_time: string;
  arrival_time: string;
  price: number;
  seats_available: number;
}

export interface Booking {
  booking_id: number;
  user_id: number;
  flight_id: number;
  status: 'booked' | 'cancelled' | 'completed';
  booking_time: string;
  infant_count: number;
}

export interface User {
  user_id: number;
  name: string;
  email: string;
}

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

// Request/Response types
export interface BookingRequest {
  user_id: number;
  name: string;
  flight_id: number;
  infant_count?: number;
}

export interface UserRegistration {
  name: string;
  email: string;
}

export interface ErrorResponse {
  success: false;
  error: string;
  error_code: string;
  details?: string;
}

// Extended types for UI
export interface BookingWithFlight extends Booking {
  flight?: Flight;
}

export interface FlightFilters {
  origin?: string;
  destination?: string;
  minPrice?: number;
  maxPrice?: number;
  searchTerm?: string;
}

// User context type
export interface UserContextType {
  user: User | null;
  setUser: (user: User | null) => void;
  logout: () => void;
}

// Made with Bob
