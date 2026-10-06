from fastapi import FastAPI, Depends, HTTPException, Request, APIRouter
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import List, Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uuid
import datetime
import secrets

# --- SQLAlchemy setup ---
from sqlalchemy import create_engine, Column, String, Integer, DateTime, func
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

class UsageRecordDB(Base):
    __tablename__ = "usage_records"
    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String, index=True)
    endpoint = Column(String)
    method = Column(String)
    status_code = Column(Integer)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)
# ------------------------

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="PartnerAPI", version="1.0.0", description="Public Hotel Booking API (SQLite backed + Sandbox + Analytics + Partner Management)")
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

class PartnerCreateRequest(BaseModel):
    partner_name: str

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to validate API Key
def get_api_key(api_key_header: str = Depends(api_key_header), db: Session = Depends(get_db)):
    key_record = db.query(PartnerAPIKeyDB).filter(PartnerAPIKeyDB.key == api_key_header).first()
    if not key_record:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return api_key_header

@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    api_key = request.headers.get("Authorization", "Anonymous")
    db = SessionLocal()
    usage = UsageRecordDB(
        api_key=api_key,
        endpoint=request.url.path,
        method=request.method,
        status_code=response.status_code
    )
    db.add(usage)
    db.commit()
    db.close()
    return response

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    if not db.query(PartnerAPIKeyDB).first():
        db.add(PartnerAPIKeyDB(key="Bearer partner-api-key", partner_name="Test Partner 1"))
    if not db.query(HotelDB).first():
        db.add(HotelDB(id="h1", name="Grand Hotel", destination="London", available_rooms=10))
        db.add(HotelDB(id="h2", name="Cozy Inn", destination="London", available_rooms=5))
    db.commit()
    db.close()

# --- ADMIN / ANALYTICS ROUTER ---
admin_router = APIRouter(prefix="/api/admin")

@admin_router.get("/reports")
def get_usage_reports(db: Session = Depends(get_db)):
    report = db.query(UsageRecordDB.api_key, func.count(UsageRecordDB.id).label("total_requests")).group_by(UsageRecordDB.api_key).all()
    return [{"api_key": r.api_key, "total_requests": r.total_requests} for r in report]

@admin_router.post("/partners")
def create_partner(partner: PartnerCreateRequest, db: Session = Depends(get_db)):
    # Generate a secure token
    raw_key = secrets.token_hex(16)
    formatted_key = f"Bearer {raw_key}"
    
    new_partner = PartnerAPIKeyDB(key=formatted_key, partner_name=partner.partner_name)
    db.add(new_partner)
    db.commit()
    return {"partner_name": partner.partner_name, "api_key": formatted_key}

@admin_router.delete("/partners/{partner_name}")
def delete_partner(partner_name: str, db: Session = Depends(get_db)):
    partners = db.query(PartnerAPIKeyDB).filter(PartnerAPIKeyDB.partner_name == partner_name).all()
    if not partners:
        raise HTTPException(status_code=404, detail="Partner not found")
    for p in partners:
        db.delete(p)
    db.commit()
    return {"message": f"Partner {partner_name} and keys revoked."}


# --- PRODUCTION API ROUTER ---
prod_router = APIRouter(prefix="/api/v1")

@prod_router.get("/hotels/search", response_model=List[HotelResponse])
@limiter.limit("100/minute")
def search_hotels(request: Request, destination: str, checkIn: str, checkOut: str, guests: int, rooms: int, api_key: str = Depends(get_api_key), db: Session = Depends(get_db)):
    hotels = db.query(HotelDB).filter(HotelDB.destination.ilike(destination), HotelDB.available_rooms >= rooms).all()
    return hotels

@prod_router.post("/bookings", response_model=BookingResponse)
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

@prod_router.get("/bookings/{booking_id}", response_model=BookingResponse)
@limiter.limit("100/minute")
def retrieve_booking(request: Request, booking_id: str, api_key: str = Depends(get_api_key), db: Session = Depends(get_db)):
    booking = db.query(BookingDB).filter(BookingDB.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@prod_router.post("/bookings/{booking_id}/cancel")
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


# --- SANDBOX API ROUTER ---
sandbox_router = APIRouter(prefix="/api/sandbox/v1")
sandbox_hotels = [
    {"id": "test_h1", "name": "Sandbox Hotel 1", "destination": "Paris", "available_rooms": 100},
    {"id": "test_h2", "name": "Sandbox Hotel 2", "destination": "Paris", "available_rooms": 20},
]
sandbox_bookings = {}

@sandbox_router.get("/hotels/search", response_model=List[HotelResponse])
@limiter.limit("100/minute")
def sandbox_search_hotels(request: Request, destination: str, checkIn: str, checkOut: str, guests: int, rooms: int, api_key: str = Depends(get_api_key)):
    results = [h for h in sandbox_hotels if h["destination"].lower() == destination.lower() and h["available_rooms"] >= rooms]
    return results

@sandbox_router.post("/bookings", response_model=BookingResponse)
@limiter.limit("50/minute")
def sandbox_create_booking(request: Request, booking: BookingRequest, api_key: str = Depends(get_api_key)):
    hotel = next((h for h in sandbox_hotels if h["id"] == booking.hotel_id), None)
    if not hotel or hotel["available_rooms"] < booking.rooms:
        raise HTTPException(status_code=400, detail="Hotel not found or insufficient rooms")
    hotel["available_rooms"] -= booking.rooms
    booking_id = "test_" + str(uuid.uuid4())
    sandbox_bookings[booking_id] = {
        "id": booking_id,
        "hotel_id": booking.hotel_id,
        "rooms": booking.rooms,
        "status": "CONFIRMED"
    }
    return sandbox_bookings[booking_id]

@sandbox_router.get("/bookings/{booking_id}", response_model=BookingResponse)
@limiter.limit("100/minute")
def sandbox_retrieve_booking(request: Request, booking_id: str, api_key: str = Depends(get_api_key)):
    booking = sandbox_bookings.get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found in Sandbox")
    return booking

@sandbox_router.post("/bookings/{booking_id}/cancel")
@limiter.limit("50/minute")
def sandbox_cancel_booking(request: Request, booking_id: str, api_key: str = Depends(get_api_key)):
    booking = sandbox_bookings.get(booking_id)
    if not booking or booking["status"] == "CANCELLED":
        raise HTTPException(status_code=400, detail="Booking not found or already cancelled in Sandbox")
    booking["status"] = "CANCELLED"
    hotel = next(h for h in sandbox_hotels if h["id"] == booking["hotel_id"])
    hotel["available_rooms"] += booking["rooms"]
    return {"message": "Sandbox booking cancelled successfully", "booking_id": booking_id, "status": "CANCELLED"}


app.include_router(admin_router)
app.include_router(prod_router)
app.include_router(sandbox_router)
