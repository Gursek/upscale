from app import create_app
from models.db import db


def _json(response, status):
    assert response.status_code == status, response.get_json()
    return response.get_json()


def test_cash_sale_reprint_z_lock_and_audit_chain():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-app-secret-that-is-at-least-32-bytes",
        "JWT_SECRET_KEY": "test-jwt-secret-that-is-at-least-32-bytes",
    })
    with app.app_context():
        db.drop_all()
        db.create_all()

    client = app.test_client()
    registered = _json(client.post("/api/auth/register", json={
        "email": "compliance@example.com",
        "password": "Strong1!",
        "business_name": "Compliance Store",
        "business_address": "Manila, Philippines",
        "tin": "123-456-789",
        "vat_status": "non_vat",
    }), 201)
    headers = {"Authorization": f"Bearer {registered['access_token']}"}

    settings = _json(client.put("/api/auth/me", headers=headers, json={
        "branch_code": "00000",
        "machine_identification_number": "MIN-001",
        "machine_serial_number": "SERIAL-001",
        "accreditation_number": "ACC-001",
        "accreditation_date_issued": "2026-01-01",
        "accreditation_valid_until": "2031-01-01",
        "ptu_number": "PTU-001",
        "ptu_date_issued": "2026-01-02",
        "accredited_supplier_name": "UpScale Developer",
        "accredited_supplier_address": "Manila, Philippines",
        "accredited_supplier_tin": "987-654-321",
        "software_version": "1.0.0",
        "business_day_cutoff": "00:00",
    }), 200)
    assert settings["compliance"]["ready"] is True

    product = _json(client.post("/api/products/", headers=headers, json={
        "name": "Test Product",
        "category": "retail",
        "pricing_type": "fixed",
        "price": "25.00",
        "stock_quantity": "10",
        "unit": "pcs",
        "tax_classification": "standard",
    }), 201)

    invoice = _json(client.post("/api/invoices/", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 2}],
        "payment_mode": "cash",
        "cash_tendered": "100.00",
        "buyer_name": "Juan Dela Cruz",
        "buyer_tin": "111-222-333",
    }), 201)
    assert invoice["invoice_number"] == "000001"
    assert invoice["display_invoice_number"] == "00-000001"
    assert invoice["change_amount"] == 50.0
    assert invoice["seller"]["machine_identification_number"] == "MIN-001"

    assert client.get(
        f"/api/invoices/{invoice['id']}/print", headers=headers
    ).status_code == 200
    assert client.post(
        f"/api/invoices/{invoice['id']}/reprint", headers=headers
    ).status_code == 200

    z_reading = _json(client.post("/api/readings/z", headers=headers, json={
        "password": "Strong1!",
    }), 201)
    assert z_reading["z_counter"] == 1
    assert z_reading["cash_sales"] == 50.0

    blocked_void = client.post(
        f"/api/invoices/{invoice['id']}/void",
        headers=headers,
        json={"reason": "Wrong item"},
    )
    assert blocked_void.status_code == 409

    integrity = _json(
        client.get("/api/compliance/audit-integrity", headers=headers),
        200,
    )
    assert integrity["valid"] is True
    assert integrity["checked_events"] >= 6


def test_statutory_discount_requires_beneficiary_details():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-app-secret-that-is-at-least-32-bytes",
        "JWT_SECRET_KEY": "test-jwt-secret-that-is-at-least-32-bytes",
    })
    with app.app_context():
        db.drop_all()
        db.create_all()
    client = app.test_client()
    registered = _json(client.post("/api/auth/register", json={
        "email": "discount@example.com",
        "password": "Strong1!",
        "business_name": "Discount Store",
    }), 201)
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    product = _json(client.post("/api/products/", headers=headers, json={
        "name": "Item",
        "category": "retail",
        "pricing_type": "fixed",
        "price": "100.00",
        "stock_quantity": "2",
    }), 201)
    response = client.post("/api/invoices/", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "cash_tendered": "100.00",
        "discount_type": "senior_citizen",
        "discount_amount": "20.00",
    })
    assert response.status_code == 400
    assert "beneficiary" in response.get_json()["error"].lower()
