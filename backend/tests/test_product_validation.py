import pytest

from app import create_app
from models.db import db


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


def _json(response, status):
    assert response.status_code == status, response.get_json()
    return response.get_json()


def _headers(client):
    registered = _json(client.post("/api/auth/register", json={
        "email": "products@example.com",
        "password": "Strong1!",
        "business_name": "Product Store",
    }), 201)
    return {"Authorization": f"Bearer {registered['access_token']}"}


def _valid_product(**overrides):
    payload = {
        "name": "Ribeye",
        "category": "beef",
        "pricing_type": "per_kg",
        "price": "450.00",
        "stock_quantity": "10.500",
        "low_stock_threshold": "2",
        "unit": "kg",
        "tax_classification": "exempt",
    }
    payload.update(overrides)
    return payload


def test_valid_product_creates_successfully():
    app = _app()
    client = app.test_client()
    headers = _headers(client)

    product = _json(client.post("/api/products/", headers=headers, json=_valid_product()), 201)
    assert product["name"] == "Ribeye"
    assert product["category"] == "beef"
    assert product["pricing_type"] == "per_kg"
    assert product["price"] == 450.0
    assert product["stock_quantity"] == 10.5
    assert product["low_stock_threshold"] == 2.0
    assert product["unit"] == "kg"
    assert product["tax_classification"] == "exempt"


@pytest.mark.parametrize(("field", "value", "message"), [
    ("category", "fish", "category:"),
    ("pricing_type", "weighted", "pricing_type:"),
    ("tax_classification", "zero_rated", "tax_classification:"),
    ("price", "0", "price:"),
    ("price", "-1", "price:"),
    ("price", "abc", "price:"),
    ("stock_quantity", "-0.001", "stock_quantity:"),
    ("low_stock_threshold", "-1", "low_stock_threshold:"),
    ("low_stock_threshold", "1.5", "low_stock_threshold:"),
    ("unit", "crate", "unit:"),
])
def test_invalid_product_create_fields_return_descriptive_400(field, value, message):
    app = _app()
    client = app.test_client()
    headers = _headers(client)

    payload = _valid_product(**{field: value})
    response = client.post("/api/products/", headers=headers, json=payload)
    assert response.status_code == 400
    assert response.get_json()["error"].startswith(message)


@pytest.mark.parametrize(("field", "value", "message"), [
    ("category", "fish", "category:"),
    ("pricing_type", "weighted", "pricing_type:"),
    ("tax_classification", "zero_rated", "tax_classification:"),
    ("price", "0", "price:"),
    ("price", "-1", "price:"),
    ("price", "abc", "price:"),
    ("low_stock_threshold", "-1", "low_stock_threshold:"),
    ("low_stock_threshold", "1.5", "low_stock_threshold:"),
    ("unit", "crate", "unit:"),
])
def test_invalid_product_update_fields_return_descriptive_400(field, value, message):
    app = _app()
    client = app.test_client()
    headers = _headers(client)
    product = _json(client.post("/api/products/", headers=headers, json=_valid_product()), 201)

    response = client.put(f"/api/products/{product['id']}", headers=headers, json={field: value})
    assert response.status_code == 400
    assert response.get_json()["error"].startswith(message)
