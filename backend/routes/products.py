from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import json
import os
from uuid import uuid4
from werkzeug.utils import secure_filename

from models.db import db
from models.product import Product
from services.compliance import add_audit_event
from services.business_time import to_business_iso

products_bp = Blueprint("products", __name__)
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def _product_to_dict(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "cut_type": p.cut_type,
        "pricing_type": p.pricing_type,
        "price": float(p.price),
        "unit": p.unit,
        "sku": p.sku,
        "stock_quantity": float(p.stock_quantity),
        "low_stock_threshold": float(p.low_stock_threshold),
        "tax_classification": p.tax_classification,
        "image_url": p.image_url,
        "is_active": p.is_active,
        "is_archived": p.is_archived,
        "archived_at": to_business_iso(p.archived_at),
    }


def _default_tax_classification(category: str) -> str:
    return "exempt" if category in ("beef", "pork", "chicken", "fish", "veggies") else "standard"


def _log_action(user_id, entity_id, action, before=None, after=None):
    add_audit_event(
        user_id=user_id,
        entity_type="product",
        entity_id=entity_id,
        action=action,
        before=before,
        after=after,
    )


@products_bp.route("/upload-image", methods=["POST"])
@jwt_required()
def upload_product_image():
    user_id = int(get_jwt_identity())
    image = request.files.get("image")
    if not image or not image.filename:
        return jsonify({"error": "Image file is required"}), 400

    filename = secure_filename(image.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({"error": "Use a PNG, JPG, JPEG, or WEBP image"}), 400

    image.seek(0, os.SEEK_END)
    size = image.tell()
    image.seek(0)
    if size > 5 * 1024 * 1024:
        return jsonify({"error": "Image must be 5 MB or smaller"}), 400

    relative_dir = os.path.join("uploads", "products", str(user_id))
    upload_dir = os.path.join(current_app.static_folder, relative_dir)
    os.makedirs(upload_dir, exist_ok=True)
    stored_name = f"{uuid4().hex}.{extension}"
    image.save(os.path.join(upload_dir, stored_name))

    image_url = f"/static/{relative_dir.replace(os.sep, '/')}/{stored_name}"
    return jsonify({"image_url": image_url}), 201


@products_bp.route("/", methods=["GET"])
@jwt_required()
def list_products():
    user_id = int(get_jwt_identity())
    category = request.args.get("category")

    query = Product.query.filter_by(user_id=user_id, is_archived=False)
    if category:
        query = query.filter_by(category=category)

    products = query.order_by(Product.name).all()
    return jsonify([_product_to_dict(p) for p in products]), 200


@products_bp.route("/archived", methods=["GET"])
@jwt_required()
def list_archived_products():
    user_id = int(get_jwt_identity())
    products = Product.query.filter_by(user_id=user_id, is_archived=True).order_by(Product.archived_at.desc()).all()
    return jsonify([_product_to_dict(p) for p in products]), 200


@products_bp.route("/", methods=["POST"])
@jwt_required()
def create_product():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    required = ["name", "category", "pricing_type", "price"]
    if not all(field in data and data[field] not in (None, "") for field in required):
        return jsonify({"error": "Missing required fields"}), 400

    product = Product(
        user_id=user_id,
        name=data["name"],
        category=data["category"],
        cut_type=data.get("cut_type"),
        pricing_type=data["pricing_type"],
        price=data["price"],
        unit=data.get("unit", "kg" if data["category"] != "retail" else "pcs"),
        sku=data.get("sku"),
        stock_quantity=data.get("stock_quantity", 0),
        low_stock_threshold=data.get("low_stock_threshold", 0),
        tax_classification=data.get("tax_classification") or _default_tax_classification(data["category"]),
        image_url=data.get("image_url"),
    )
    db.session.add(product)
    db.session.flush()  # get product.id before commit

    _log_action(user_id, product.id, "create", after=_product_to_dict(product))
    db.session.commit()

    return jsonify(_product_to_dict(product)), 201


@products_bp.route("/<int:product_id>", methods=["PUT"])
@jwt_required()
def update_product(product_id):
    user_id = int(get_jwt_identity())
    product = Product.query.filter_by(id=product_id, user_id=user_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    before = _product_to_dict(product)
    data = request.get_json()

    for field in ["name", "category", "cut_type", "pricing_type", "price", "unit",
                   "sku", "stock_quantity", "low_stock_threshold", "tax_classification",
                   "image_url", "is_active"]:
        if field in data:
            setattr(product, field, data[field])

    product.updated_at = datetime.utcnow()
    db.session.flush()

    _log_action(user_id, product.id, "update", before=before, after=_product_to_dict(product))
    db.session.commit()

    return jsonify(_product_to_dict(product)), 200


@products_bp.route("/<int:product_id>/archive", methods=["POST"])
@jwt_required()
def archive_product(product_id):
    user_id = int(get_jwt_identity())
    product = Product.query.filter_by(id=product_id, user_id=user_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    before = _product_to_dict(product)
    product.is_archived = True
    product.archived_at = datetime.utcnow()
    db.session.flush()

    _log_action(user_id, product.id, "archive", before=before, after=_product_to_dict(product))
    db.session.commit()

    return jsonify({"message": "Product archived"}), 200


@products_bp.route("/<int:product_id>/restore", methods=["POST"])
@jwt_required()
def restore_product(product_id):
    user_id = int(get_jwt_identity())
    product = Product.query.filter_by(id=product_id, user_id=user_id, is_archived=True).first()
    if not product:
        return jsonify({"error": "Archived product not found"}), 404

    before = _product_to_dict(product)
    product.is_archived = False
    product.archived_at = None
    db.session.flush()

    _log_action(user_id, product.id, "restore", before=before, after=_product_to_dict(product))
    db.session.commit()

    return jsonify({"message": "Product restored"}), 200


@products_bp.route("/<int:product_id>", methods=["DELETE"])
@jwt_required()
def delete_product(product_id):
    user_id = int(get_jwt_identity())
    product = Product.query.filter_by(id=product_id, user_id=user_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    if not product.is_archived:
        return jsonify({"error": "Product must be archived before permanent deletion"}), 400

    before = _product_to_dict(product)
    _log_action(user_id, product.id, "delete", before=before)

    db.session.delete(product)
    db.session.commit()

    return jsonify({"message": "Product permanently deleted"}), 200
