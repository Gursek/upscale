from datetime import datetime

from app import create_app
from models.db import db
from models.invoice import Invoice
from models.user import User


def _json(response, status):
    assert response.status_code == status, response.get_json()
    return response.get_json()


def _vat_discount_fixture(email):
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
        "email": email,
        "password": "Strong1!",
        "business_name": "VAT Discount Store",
        "vat_status": "vat",
    }), 201)
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    product = _json(client.post("/api/products/", headers=headers, json={
        "name": "VATable Item",
        "category": "retail",
        "pricing_type": "fixed",
        "price": "112.00",
        "stock_quantity": "10",
        "tax_classification": "standard",
    }), 201)
    return client, headers, product


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

    duplicate_z = client.post("/api/readings/z", headers=headers, json={
        "password": "Strong1!",
    })
    assert duplicate_z.status_code == 409

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


def test_statutory_discount_requires_id_number():
    client, headers, product = _vat_discount_fixture("missing-id-discount@example.com")
    response = client.post("/api/invoices/", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "cash_tendered": "100.00",
        "discount_type": "senior_citizen",
    })
    assert response.status_code == 400
    assert "id number" in response.get_json()["error"].lower()


def test_senior_citizen_discount_computes_server_side_for_vatable_invoice():
    client, headers, product = _vat_discount_fixture("sc-discount@example.com")
    invoice = _json(client.post("/api/invoices/", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "cash_tendered": "100.00",
        "discount_type": "senior_citizen",
        "discount_id_no": "SC-12345",
    }), 201)
    assert invoice["subtotal"] == 112.0
    assert invoice["vatable_sales"] == 100.0
    assert invoice["vat_amount"] == 12.0
    assert invoice["discount_amount"] == 20.0
    assert invoice["vat_deduction"] == 12.0
    assert invoice["total_amount"] == 80.0


def test_pwd_discount_matches_senior_citizen_discount():
    client, headers, product = _vat_discount_fixture("pwd-discount@example.com")
    invoice = _json(client.post("/api/invoices/", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "cash_tendered": "100.00",
        "discount_type": "pwd",
        "discount_id_no": "PWD-12345",
    }), 201)
    assert invoice["discount_amount"] == 20.0
    assert invoice["vat_deduction"] == 12.0
    assert invoice["total_amount"] == 80.0


def test_client_sent_discount_amount_is_ignored():
    client, headers, product = _vat_discount_fixture("ignored-discount@example.com")
    invoice = _json(client.post("/api/invoices/", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "cash_tendered": "100.00",
        "discount_type": "senior_citizen",
        "discount_id_no": "SC-99999",
        "discount_amount": "999.00",
    }), 201)
    assert invoice["discount_amount"] == 20.0
    assert invoice["vat_deduction"] == 12.0
    assert invoice["total_amount"] == 80.0


def test_invoice_serialized_datetime_uses_manila_time():
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
        "email": "timezone@example.com",
        "password": "Strong1!",
        "business_name": "Timezone Store",
    }), 201)
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    product = _json(client.post("/api/products/", headers=headers, json={
        "name": "Time Item",
        "category": "retail",
        "pricing_type": "fixed",
        "price": "50.00",
        "stock_quantity": "2",
    }), 201)
    created = _json(client.post("/api/invoices/", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "cash_tendered": "100.00",
    }), 201)

    with app.app_context():
        invoice = Invoice.query.get(created["id"])
        invoice.date_time = datetime(2026, 6, 16, 23, 30, 0)
        db.session.commit()

    invoice = _json(client.get(f"/api/invoices/{created['id']}", headers=headers), 200)
    assert invoice["date_time"] == "2026-06-17 07:30:00"


def test_product_update_blocks_direct_stock_changes():
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
        "email": "stock-edit@example.com",
        "password": "Strong1!",
        "business_name": "Stock Edit Store",
    }), 201)
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    product = _json(client.post("/api/products/", headers=headers, json={
        "name": "Stock Item",
        "category": "retail",
        "pricing_type": "fixed",
        "price": "100.00",
        "stock_quantity": "5",
    }), 201)

    blocked = client.put(f"/api/products/{product['id']}", headers=headers, json={
        "stock_quantity": "8",
    })
    assert blocked.status_code == 400
    assert "inventory" in blocked.get_json()["error"].lower()

    updated = _json(client.put(f"/api/products/{product['id']}", headers=headers, json={
        "name": "Renamed Stock Item",
        "price": "110.00",
    }), 200)
    assert updated["name"] == "Renamed Stock Item"
    assert updated["stock_quantity"] == 5.0


def test_cashier_permissions_allow_sales_but_block_management_and_z_reading():
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
        "email": "cashier@example.com",
        "password": "Strong1!",
        "business_name": "Cashier Store",
    }), 201)
    headers = {"Authorization": f"Bearer {registered['access_token']}"}

    product = _json(client.post("/api/products/", headers=headers, json={
        "name": "Cashier Item",
        "category": "retail",
        "pricing_type": "fixed",
        "price": "50.00",
        "stock_quantity": "3",
    }), 201)

    with app.app_context():
        user = User.query.get(registered["user"]["id"])
        user.role = "cashier"
        db.session.commit()

    blocked_product = client.post("/api/products/", headers=headers, json={
        "name": "Blocked Item",
        "category": "retail",
        "pricing_type": "fixed",
        "price": "10.00",
    })
    assert blocked_product.status_code == 403

    invoice = _json(client.post("/api/invoices/", headers=headers, json={
        "items": [{"product_id": product["id"], "quantity": 1}],
        "cash_tendered": "100.00",
    }), 201)
    assert invoice["total_amount"] == 50.0

    blocked_z = client.post("/api/readings/z", headers=headers, json={
        "password": "Strong1!",
    })
    assert blocked_z.status_code == 403
