from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import json

from models.db import db
from models.supplier import Supplier
from services.compliance import add_audit_event
from services.business_time import to_business_iso
from services.rbac import roles_required

suppliers_bp = Blueprint("suppliers", __name__)


def _supplier_to_dict(s: Supplier) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "contact_info": s.contact_info,
        "products_supplied": s.products_supplied,
        "is_archived": s.is_archived,
        "archived_at": to_business_iso(s.archived_at),
        "created_at": to_business_iso(s.created_at),
    }


def _log_action(user_id, entity_id, action, before=None, after=None):
    add_audit_event(
        user_id=user_id,
        entity_type="supplier",
        entity_id=entity_id,
        action=action,
        before=before,
        after=after,
    )


@suppliers_bp.route("/", methods=["GET"])
@jwt_required()
@roles_required("owner", "manager")
def list_suppliers():
    user_id = int(get_jwt_identity())
    suppliers = Supplier.query.filter_by(
        user_id=user_id, is_archived=False
    ).order_by(Supplier.name).all()
    return jsonify([_supplier_to_dict(s) for s in suppliers]), 200


@suppliers_bp.route("/archived", methods=["GET"])
@jwt_required()
@roles_required("owner", "manager")
def list_archived_suppliers():
    user_id = int(get_jwt_identity())
    suppliers = Supplier.query.filter_by(
        user_id=user_id, is_archived=True
    ).order_by(Supplier.archived_at.desc()).all()
    return jsonify([_supplier_to_dict(s) for s in suppliers]), 200


@suppliers_bp.route("/", methods=["POST"])
@jwt_required()
@roles_required("owner", "manager")
def create_supplier():
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data.get("name"):
        return jsonify({"error": "Supplier name is required"}), 400

    supplier = Supplier(
        user_id=user_id,
        name=data["name"],
        contact_info=data.get("contact_info"),
        products_supplied=data.get("products_supplied"),
    )
    db.session.add(supplier)
    db.session.flush()

    _log_action(user_id, supplier.id, "create", after=_supplier_to_dict(supplier))
    db.session.commit()

    return jsonify(_supplier_to_dict(supplier)), 201


@suppliers_bp.route("/<int:supplier_id>", methods=["PUT"])
@jwt_required()
@roles_required("owner", "manager")
def update_supplier(supplier_id):
    user_id = int(get_jwt_identity())
    supplier = Supplier.query.filter_by(id=supplier_id, user_id=user_id).first()
    if not supplier:
        return jsonify({"error": "Supplier not found"}), 404

    before = _supplier_to_dict(supplier)
    data = request.get_json()

    for field in ["name", "contact_info", "products_supplied"]:
        if field in data:
            setattr(supplier, field, data[field])

    db.session.flush()
    _log_action(user_id, supplier.id, "update", before=before, after=_supplier_to_dict(supplier))
    db.session.commit()

    return jsonify(_supplier_to_dict(supplier)), 200


@suppliers_bp.route("/<int:supplier_id>/archive", methods=["POST"])
@jwt_required()
@roles_required("owner", "manager")
def archive_supplier(supplier_id):
    user_id = int(get_jwt_identity())
    supplier = Supplier.query.filter_by(id=supplier_id, user_id=user_id).first()
    if not supplier:
        return jsonify({"error": "Supplier not found"}), 404

    before = _supplier_to_dict(supplier)
    supplier.is_archived = True
    supplier.archived_at = datetime.utcnow()

    db.session.flush()
    _log_action(user_id, supplier.id, "archive", before=before, after=_supplier_to_dict(supplier))
    db.session.commit()

    return jsonify({"message": "Supplier archived"}), 200


@suppliers_bp.route("/<int:supplier_id>/restore", methods=["POST"])
@jwt_required()
@roles_required("owner", "manager")
def restore_supplier(supplier_id):
    user_id = int(get_jwt_identity())
    supplier = Supplier.query.filter_by(
        id=supplier_id, user_id=user_id, is_archived=True
    ).first()
    if not supplier:
        return jsonify({"error": "Archived supplier not found"}), 404

    before = _supplier_to_dict(supplier)
    supplier.is_archived = False
    supplier.archived_at = None

    db.session.flush()
    _log_action(user_id, supplier.id, "restore", before=before, after=_supplier_to_dict(supplier))
    db.session.commit()

    return jsonify({"message": "Supplier restored"}), 200


@suppliers_bp.route("/<int:supplier_id>", methods=["DELETE"])
@jwt_required()
@roles_required("owner", "manager")
def delete_supplier(supplier_id):
    user_id = int(get_jwt_identity())
    supplier = Supplier.query.filter_by(id=supplier_id, user_id=user_id).first()
    if not supplier:
        return jsonify({"error": "Supplier not found"}), 404

    if not supplier.is_archived:
        return jsonify({"error": "Supplier must be archived before permanent deletion"}), 400

    before = _supplier_to_dict(supplier)
    _log_action(user_id, supplier.id, "delete", before=before)

    db.session.delete(supplier)
    db.session.commit()

    return jsonify({"message": "Supplier permanently deleted"}), 200
