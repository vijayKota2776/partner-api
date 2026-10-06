from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import List, Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uuid
import datetime

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="PartnerAPI", version="1.0.0", description="Public Hotel Booking API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

API_KEY_NAME = "Authorization"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# Mock Data
VALID_API_KEYS = {"Bearer partner-api-key"}
hotels_db = [
    {"id": "h1", "name": "Grand Hotel", "destination": "London", "available_rooms": 10},
    {"id": "h2", "name": "Cozy Inn", "destination": "London", "available_rooms": 5},
]
bookings_db = {}

# Models
class HotelResponse(BaseModel):
    id: str
    name: str
    destination: str
    available_rooms: int

class BookingRequest(BaseModel):
    hotel_id: str
    rooms: int
    guest_name: str

class BookingResponse(BaseModel):
    id: str
    hotel_id: str
    rooms: int
    status: str

# Dependencies
def get_api_key(api_key_header: str = Depends(api_key_header)):
    if api_key_header not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key_header

@app.get("/api/v1/hotels/search", response_model=List[HotelResponse])
@limiter.limit("100/minute")
def search_hotels(request: Request, destination: str, checkIn: str, checkOut: str, guests: int, rooms: int, api_key: str = Depends(get_api_key)):
    results = [h for h in hotels_db if h["destination"].lower() == destination.lower() and h["available_rooms"] >= rooms]
    return results

@app.post("/api/v1/bookings", response_model=BookingResponse)
@limiter.limit("50/minute")
def create_booking(request: Request, booking: BookingRequest, api_key: str = Depends(get_api_key)):
    hotel = next((h for h in hotels_db if h["id"] == booking.hotel_id), None)
    if not hotel or hotel["available_rooms"] < booking.rooms:
        raise HTTPException(status_code=400, detail="Hotel not found or insufficient rooms")
    
    hotel["available_rooms"] -= booking.rooms
    booking_id = str(uuid.uuid4())
    bookings_db[booking_id] = {
        "id": booking_id,
        "hotel_id": booking.hotel_id,
        "rooms": booking.rooms,
        "status": "CONFIRMED"
    }
    return bookings_db[booking_id]

@app.get("/api/v1/bookings/{booking_id}", response_model=BookingResponse)
@limiter.limit("100/minute")
def retrieve_booking(request: Request, booking_id: str, api_key: str = Depends(get_api_key)):
    booking = bookings_db.get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@app.post("/api/v1/bookings/{booking_id}/cancel")
@limiter.limit("50/minute")
def cancel_booking(request: Request, booking_id: str, api_key: str = Depends(get_api_key)):
    booking = bookings_db.get(booking_id)
    if not booking or booking["status"] == "CANCELLED":
        raise HTTPException(status_code=400, detail="Booking not found or already cancelled")
    
    booking["status"] = "CANCELLED"
    hotel = next(h for h in hotels_db if h["id"] == booking["hotel_id"])
    hotel["available_rooms"] += booking["rooms"]
    return {"message": "Booking cancelled successfully", "booking_id": booking_id, "status": "CANCELLED"}
