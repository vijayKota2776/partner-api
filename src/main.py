from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import List, Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uuid
import datetime

# --- SQLAlchemy setup ---
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker, Session, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./partner_api.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class HotelDB(Base):
    __tablename__ = "hotels"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    destination = Column(String, index=True)
    available_rooms = Column(Integer)

class BookingDB(Base):
    __tablename__ = "bookings"
    id = Column(String, primary_key=True, index=True)
    hotel_id = Column(String, index=True)
    rooms = Column(Integer)
    status = Column(String)

class PartnerAPIKeyDB(Base):
    __tablename__ = "api_keys"
    key = Column(String, primary_key=True, index=True)
    partner_name = Column(String)

Base.metadata.create_all(bind=engine)
# ------------------------

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="PartnerAPI", version="1.0.0", description="Public Hotel Booking API (SQLite backed)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

API_KEY_NAME = "Authorization"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# Models
class HotelResponse(BaseModel):
    id: str
    name: str
    destination: str
    available_rooms: int

    class Config:
        from_attributes = True

class BookingRequest(BaseModel):
    hotel_id: str
    rooms: int
    guest_name: str

class BookingResponse(BaseModel):
    id: str
    hotel_id: str
    rooms: int
    status: str

    class Config:
        from_attributes = True

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to validate API Key
def get_api_key(api_key_header: str = Depends(api_key_header), db: Session = Depends(get_db)):
    # Check if key exists in DB
    key_record = db.query(PartnerAPIKeyDB).filter(PartnerAPIKeyDB.key == api_key_header).first()
    if not key_record:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key_header

@app.on_event("startup")
def startup_event():
    # Seed DB with initial data if empty
    db = SessionLocal()
    if not db.query(PartnerAPIKeyDB).first():
        db.add(PartnerAPIKeyDB(key="Bearer partner-api-key", partner_name="Test Partner 1"))
    if not db.query(HotelDB).first():
        db.add(HotelDB(id="h1", name="Grand Hotel", destination="London", available_rooms=10))
        db.add(HotelDB(id="h2", name="Cozy Inn", destination="London", available_rooms=5))
    db.commit()
    db.close()

@app.get("/api/v1/hotels/search", response_model=List[HotelResponse])
@limiter.limit("100/minute")
def search_hotels(request: Request, destination: str, checkIn: str, checkOut: str, guests: int, rooms: int, api_key: str = Depends(get_api_key), db: Session = Depends(get_db)):
    hotels = db.query(HotelDB).filter(HotelDB.destination.ilike(destination), HotelDB.available_rooms >= rooms).all()
    return hotels

@app.post("/api/v1/bookings", response_model=BookingResponse)
@limiter.limit("50/minute")
def create_booking(request: Request, booking: BookingRequest, api_key: str = Depends(get_api_key), db: Session = Depends(get_db)):
    hotel = db.query(HotelDB).filter(HotelDB.id == booking.hotel_id).first()
    if not hotel or hotel.available_rooms < booking.rooms:
        raise HTTPException(status_code=400, detail="Hotel not found or insufficient rooms")
    
    hotel.available_rooms -= booking.rooms
    
    booking_id = str(uuid.uuid4())
    new_booking = BookingDB(id=booking_id, hotel_id=booking.hotel_id, rooms=booking.rooms, status="CONFIRMED")
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking

@app.get("/api/v1/bookings/{booking_id}", response_model=BookingResponse)
@limiter.limit("100/minute")
def retrieve_booking(request: Request, booking_id: str, api_key: str = Depends(get_api_key), db: Session = Depends(get_db)):
    booking = db.query(BookingDB).filter(BookingDB.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@app.post("/api/v1/bookings/{booking_id}/cancel")
@limiter.limit("50/minute")
def cancel_booking(request: Request, booking_id: str, api_key: str = Depends(get_api_key), db: Session = Depends(get_db)):
    booking = db.query(BookingDB).filter(BookingDB.id == booking_id).first()
    if not booking or booking.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Booking not found or already cancelled")
    
    booking.status = "CANCELLED"
    hotel = db.query(HotelDB).filter(HotelDB.id == booking.hotel_id).first()
    if hotel:
        hotel.available_rooms += booking.rooms
        
    db.commit()
    return {"message": "Booking cancelled successfully", "booking_id": booking_id, "status": "CANCELLED"}
