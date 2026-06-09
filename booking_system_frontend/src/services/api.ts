import axios from 'axios';
import type {
  Flight,
  Booking,
  User,
  BookingRequest,
  UserRegistration,
  ErrorResponse,
  Discount,
} from '../types';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8082',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data) {
      // Backend returned an error response
      return Promise.reject(error.response.data);
    }
    // Network or other error
    return Promise.reject({
      success: false,
      error: 'Network error',
      error_code: 'NETWORK_ERROR',
      details: error.message,
    } as ErrorResponse);
  }
);

// ==================== Flight Endpoints ====================

/**
 * Get all available flights
 */
export const getFlights = async (): Promise<Flight[]> => {
  const response = await api.get<Flight[]>('/flights');
  return response.data;
};

// ==================== User Endpoints ====================

/**
 * Register a new user
 */
export const registerUser = async (
  data: UserRegistration
): Promise<User | ErrorResponse> => {
  const response = await api.post<User | ErrorResponse>('/register', data);
  return response.data;
};

/**
 * Get user by name and email
 */
export const getUserByCredentials = async (
  name: string,
  email: string
): Promise<User | ErrorResponse> => {
  const response = await api.get<User | ErrorResponse>('/user', {
    params: { name, email },
  });
  return response.data;
};

// ==================== Booking Endpoints ====================

/**
 * Book a flight
 */
export const bookFlight = async (
  data: BookingRequest
): Promise<Booking | ErrorResponse> => {
  const response = await api.post<Booking | ErrorResponse>('/book', data);
  return response.data;
};

/**
 * Get all bookings for a user
 */
export const getUserBookings = async (userId: number): Promise<Booking[]> => {
  const response = await api.get<Booking[]>(`/bookings/${userId}`);
  return response.data;
};

/**
 * Cancel a booking
 */
export const cancelBooking = async (
  bookingId: number
): Promise<Booking | ErrorResponse> => {
  const response = await api.post<Booking | ErrorResponse>(
    `/cancel/${bookingId}`
  );
  return response.data;
};

// ==================== Discount Endpoints ====================

/**
 * Get all discounts
 */
export const getAllDiscounts = async (): Promise<Discount[]> => {
  const response = await api.get<Discount[]>('/discounts');
  return response.data;
};

/**
 * Get discount by booking ID
 */
export const getDiscountByBooking = async (
  bookingId: number
): Promise<Discount | null> => {
  const response = await api.get<Discount | null>(`/discounts/booking/${bookingId}`);
  return response.data;
};

/**
 * Get discounts by user email
 */
export const getDiscountsByUserEmail = async (
  email: string
): Promise<Discount[]> => {
  const response = await api.get<Discount[]>(`/discounts/user/${email}`);
  return response.data;
};

// ==================== Helper Functions ====================

/**
 * Check if response is an error
 */
export const isErrorResponse = (
  response: any
): response is ErrorResponse => {
  return response && response.success === false;
};

/**
 * Health check
 */
export const healthCheck = async (): Promise<{ status: string }> => {
  const response = await api.get<{ status: string }>('/');
  return response.data;
};

export default api;

// Made with Bob
