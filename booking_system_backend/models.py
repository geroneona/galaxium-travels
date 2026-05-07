from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

class Flight(Base):
    __tablename__ = 'flights'
    flight_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_time = Column(String, nullable=False)
    arrival_time = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    seats_available = Column(Integer, nullable=False)

class Booking(Base):
    __tablename__ = 'bookings'
    booking_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    flight_id = Column(Integer, ForeignKey('flights.flight_id'), nullable=False)
    status = Column(String, nullable=False)
    booking_time = Column(String, nullable=False)
    infant_count = Column(Integer, nullable=False, default=0)

class Discount(Base):
    __tablename__ = 'discounts'
    discount_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    booking_id = Column(Integer, ForeignKey('bookings.booking_id'), nullable=False)
    infant_count = Column(Integer, nullable=False, default=0)
    original_price = Column(Integer, nullable=False)
    discounted_price_per_infant = Column(Integer, nullable=False)
    applied_discounted_price_per_infant_count = Column(Integer, nullable=False)
    flight_id = Column(Integer, ForeignKey('flights.flight_id'), nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_time = Column(String, nullable=False)
    arrival_time = Column(String, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)