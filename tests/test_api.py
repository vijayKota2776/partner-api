import pytest
from fastapi.testclient import TestClient
from src.main import app, SessionLocal, Base, engine, PartnerAPIKeyDB, HotelDB

client = TestClient(app)

def setup_module(module):
    # Setup test DB (which points to the SQLite DB)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    # Add a test API key for testing
    if not db.query(PartnerAPIKeyDB).filter_by(key="Bearer test-api-key").first():
        db.add(PartnerAPIKeyDB(key="Bearer test-api-key", partner_name="PyTest Partner"))
    # Add a test hotel
    if not db.query(HotelDB).filter_by(id="test_h1").first():
        db.add(HotelDB(id="test_h1", name="Test Hotel", destination="TestCity", available_rooms=2))
    db.commit()
    db.close()

def test_search_hotels_unauthorized():
    response = client.get("/api/v1/hotels/search?destination=London&checkIn=2023-01-01&checkOut=2023-01-05&guests=2&rooms=1")
    assert response.status_code == 401

def test_search_hotels_authorized():
    response = client.get(
        "/api/v1/hotels/search?destination=TestCity&checkIn=2023-01-01&checkOut=2023-01-05&guests=2&rooms=1",
        headers={"Authorization": "Bearer test-api-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["destination"] == "TestCity"

def test_sandbox_search():
    response = client.get(
        "/api/sandbox/v1/hotels/search?destination=Paris&checkIn=2023-01-01&checkOut=2023-01-05&guests=2&rooms=1",
        headers={"Authorization": "Bearer test-api-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

def test_create_and_retrieve_booking():
    headers = {"Authorization": "Bearer test-api-key"}
    # Create
    response = client.post(
        "/api/v1/bookings",
        headers=headers,
        json={"hotel_id": "test_h1", "rooms": 1, "guest_name": "John Doe"}
    )
    assert response.status_code == 200
    booking_id = response.json()["id"]

    # Retrieve
    retrieve_response = client.get(f"/api/v1/bookings/{booking_id}", headers=headers)
    assert retrieve_response.status_code == 200
    assert retrieve_response.json()["hotel_id"] == "test_h1"

def test_admin_reports():
    # Reports should track the above requests
    response = client.get("/api/admin/reports")
    assert response.status_code == 200
    data = response.json()
    # Find test-api-key in reports
    test_report = next((item for item in data if item["api_key"] == "Bearer test-api-key"), None)
    assert test_report is not None
    assert test_report["total_requests"] > 0
