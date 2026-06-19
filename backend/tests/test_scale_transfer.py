from datetime import datetime, timedelta
import os
from unittest.mock import patch

from app import create_app
from models.db import db
from scripts.scale_push_bridge import transfer_once


def _app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-app-secret-that-is-at-least-32-bytes",
        "JWT_SECRET_KEY": "test-jwt-secret-that-is-at-least-32-bytes",
    })
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app


def _register(client):
    registered = client.post("/api/auth/register", json={
        "email": "scale-owner@example.com",
        "password": "Strong1!",
        "business_name": "Scale Store",
    }).get_json()
    return registered, {"Authorization": f"Bearer {registered['access_token']}"}


@patch.dict(os.environ, {
    "SCALE_INGEST_API_KEY": "test-scale-secret",
    "SCALE_MAX_AGE_SECONDS": "10",
}, clear=False)
def test_pi_push_is_available_to_authenticated_pos():
    app = _app()
    client = app.test_client()
    registered, headers = _register(client)

    pushed = client.post("/api/scale/readings", headers={
        "X-Scale-Key": "test-scale-secret",
    }, json={
        "user_id": registered["user"]["id"],
        "device_id": "pi-vda-01",
        "weight_kg": 1.275,
        "stable": True,
        "captured_at": datetime.utcnow().isoformat() + "Z",
    })
    assert pushed.status_code == 201
    assert pushed.get_json()["accepted"] is True

    reading = client.get("/api/scale/read", headers=headers)
    assert reading.status_code == 200
    assert reading.get_json()["weight_kg"] == 1.275
    assert reading.get_json()["device_id"] == "pi-vda-01"
    assert reading.get_json()["stale"] is False


@patch.dict(os.environ, {"SCALE_INGEST_API_KEY": "test-scale-secret"}, clear=False)
def test_push_rejects_bad_credentials_and_unstable_readings():
    app = _app()
    client = app.test_client()
    registered, _ = _register(client)

    unauthorized = client.post("/api/scale/readings", json={
        "user_id": registered["user"]["id"],
        "weight_kg": 1,
    })
    assert unauthorized.status_code == 401

    unstable = client.post("/api/scale/readings", headers={
        "X-Scale-Key": "test-scale-secret",
    }, json={
        "user_id": registered["user"]["id"],
        "weight_kg": 1,
        "stable": False,
    })
    assert unstable.status_code == 422


@patch.dict(os.environ, {
    "SCALE_INGEST_API_KEY": "test-scale-secret",
    "SCALE_MAX_AGE_SECONDS": "2",
    "SCALE_MAX_INGEST_AGE_SECONDS": "60",
}, clear=False)
def test_pos_rejects_stale_reading():
    app = _app()
    client = app.test_client()
    registered, headers = _register(client)
    captured_at = datetime.utcnow() - timedelta(seconds=5)

    pushed = client.post("/api/scale/readings", headers={
        "X-Scale-Key": "test-scale-secret",
    }, json={
        "user_id": registered["user"]["id"],
        "weight_kg": 0.850,
        "captured_at": captured_at.isoformat() + "Z",
    })
    assert pushed.status_code == 201

    reading = client.get("/api/scale/read", headers=headers)
    assert reading.status_code == 503
    assert reading.get_json()["stale"] is True


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self):
        self.posted = None

    def get(self, url, timeout):
        assert url == "http://pi.local/read"
        assert timeout == 2
        return _FakeResponse({
            "weight_kg": 2.125,
            "stable": True,
            "captured_at": "2026-06-19T02:00:00Z",
        })

    def post(self, url, json, headers, timeout):
        self.posted = {
            "url": url,
            "json": json,
            "headers": headers,
            "timeout": timeout,
        }
        return _FakeResponse({"accepted": True, "reading_id": 17})


@patch.dict(os.environ, {
    "PI_SCALE_READ_URL": "http://pi.local/read",
    "UPSCALE_SCALE_INGEST_URL": "https://api.example.com/api/scale/readings",
    "SCALE_INGEST_API_KEY": "device-secret",
    "SCALE_USER_ID": "7",
    "SCALE_TRANSFER_TIMEOUT_SECONDS": "2",
}, clear=False)
def test_bridge_transfers_existing_pi_service_contract():
    session = _FakeSession()
    result = transfer_once(session=session)

    assert result["transferred"] is True
    assert session.posted["json"]["weight_kg"] == 2.125
    assert session.posted["json"]["user_id"] == 7
    assert session.posted["headers"]["X-Scale-Key"] == "device-secret"
