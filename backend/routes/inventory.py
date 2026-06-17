from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from decimal import Decimal
import json

from models.db import db
from models.audit_log import AuditLog
from models.product import Product
from models.user import User
from services.compliance import add_audit_event
from models.ejournal import EJournalEntry
from services.business_time import business_today, to_business_iso
from services.rbac import roles_required

inventory_bp = Blueprint("inventory", __name__)

INVENTORY_HISTORY_ACTIONS = ("restock", "adjustment", "sale_deduction", "void_restock")


def _stock_snapshot(product: Product, **extra) -> dict:
    snapshot = {
        "product_id": product.id,
        "product_name": product.name,
        "unit": product.unit,
        "stock_quantity": float(product.stock_quantity),
    }
    snapshot.update(extra)
    return snapshot


def _log_inventory_action(user_id, product_id, action, before, after):
    add_audit_event(
        user_id=user_id,
        entity_type="product",
        entity_id=product_id,
        action=action,
        before=before,
        after=after,
    )


def _log_ejournal(user_id, product_id, snapshot):
    db.session.add(EJournalEntry(
        user_id=user_id,
        entry_date=business_today(User.query.get(user_id).business_day_cutoff),
        entry_type="adjustment",
        reference_id=product_id,
        snapshot_json=json.dumps(snapshot),
    ))


@inventory_bp.route("/restock", methods=["POST"])
@jwt_required()
@roles_required("owner", "manager")
def restock_product():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    product_id = data.get("product_id")
    if not product_id:
        return jsonify({"error": "product_id is required"}), 400

    try:
        quantity = Decimal(str(data.get("quantity", 0)))
    except Exception:
        return jsonify({"error": "Invalid quantity"}), 400

    if quantity <= 0:
        return jsonify({"error": "Quantity must be greater than zero"}), 400

    product = Product.query.filter_by(
        id=product_id, user_id=user_id, is_archived=False
    ).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    notes = (data.get("notes") or "").strip()
    if not notes:
        return jsonify({"error": "Reason is required for stock additions"}), 400

    before = _stock_snapshot(product)
    product.stock_quantity += quantity
    product.updated_at = datetime.utcnow()
    after = _stock_snapshot(product, quantity_added=float(quantity), notes=notes)

    _log_inventory_action(user_id, product.id, "restock", before, after)
    _log_ejournal(user_id, product.id, {
        "type": "restock",
        "product_id": product.id,
        "product_name": product.name,
        "quantity_added": float(quantity),
        "before_stock": before["stock_quantity"],
        "after_stock": after["stock_quantity"],
        "notes": notes,
    })

    db.session.commit()

    return jsonify({
        "message": "Stock restocked",
        "product_id": product.id,
        "stock_quantity": float(product.stock_quantity),
        "unit": product.unit,
    }), 200


@inventory_bp.route("/adjust", methods=["POST"])
@jwt_required()
@roles_required("owner", "manager")
def adjust_stock():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    product_id = data.get("product_id")
    if not product_id:
        return jsonify({"error": "product_id is required"}), 400

    reason = (data.get("reason") or "").strip()
    if not reason:
        return jsonify({"error": "Reason is required for stock adjustments"}), 400

    try:
        new_quantity = Decimal(str(data.get("new_quantity")))
    except Exception:
        return jsonify({"error": "Invalid new_quantity"}), 400

    if new_quantity < 0:
        return jsonify({"error": "Stock quantity cannot be negative"}), 400

    product = Product.query.filter_by(
        id=product_id, user_id=user_id, is_archived=False
    ).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    before = _stock_snapshot(product)
    if before["stock_quantity"] == float(new_quantity):
        return jsonify({"error": "New quantity is the same as current stock"}), 400

    product.stock_quantity = new_quantity
    product.updated_at = datetime.utcnow()
    after = _stock_snapshot(
        product,
        reason=reason,
        previous_stock=before["stock_quantity"],
        adjustment_delta=float(new_quantity) - before["stock_quantity"],
    )

    _log_inventory_action(user_id, product.id, "adjustment", before, after)
    _log_ejournal(user_id, product.id, {
        "type": "adjustment",
        "product_id": product.id,
        "product_name": product.name,
        "reason": reason,
        "before_stock": before["stock_quantity"],
        "after_stock": after["stock_quantity"],
        "adjustment_delta": after["adjustment_delta"],
    })

    db.session.commit()

    return jsonify({
        "message": "Stock adjusted",
        "product_id": product.id,
        "stock_quantity": float(product.stock_quantity),
        "unit": product.unit,
    }), 200


@inventory_bp.route("/history", methods=["GET"])
@jwt_required()
@roles_required("owner", "manager")
def inventory_history():
    user_id = int(get_jwt_identity())
    product_id = request.args.get("product_id", type=int)
    limit = min(request.args.get("limit", 50, type=int), 100)

    query = AuditLog.query.filter_by(
        user_id=user_id, entity_type="product"
    ).filter(AuditLog.action.in_(INVENTORY_HISTORY_ACTIONS))

    if product_id:
        query = query.filter_by(entity_id=product_id)

    entries = query.order_by(AuditLog.created_at.desc()).limit(limit).all()

    history = []
    for entry in entries:
        before = json.loads(entry.before_state) if entry.before_state else {}
        after = json.loads(entry.after_state) if entry.after_state else {}
        history.append({
            "id": entry.id,
            "action": entry.action,
            "product_id": entry.entity_id,
            "product_name": after.get("product_name") or before.get("product_name"),
            "unit": after.get("unit") or before.get("unit"),
            "before_stock": before.get("stock_quantity"),
            "after_stock": after.get("stock_quantity"),
            "quantity_added": after.get("quantity_added"),
            "adjustment_delta": after.get("adjustment_delta"),
            "reason": after.get("reason"),
            "notes": after.get("notes"),
            "reverted": entry.reverted,
            "created_at": to_business_iso(entry.created_at),
        })

    return jsonify(history), 200
