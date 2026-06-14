from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models.db import db
from models.user import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    required = ["email", "password", "business_name"]
    if not all(field in data and data[field] for field in required):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(
        email=data["email"],
        password_hash=generate_password_hash(data["password"]),
        business_name=data["business_name"],
        business_address=data.get("business_address"),
        tin=data.get("tin"),
        vat_status=data.get("vat_status", "non_vat"),
    )
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "business_name": user.business_name,
            "onboarding_completed": user.onboarding_completed,
        }
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    user = User.query.filter_by(email=data.get("email")).first()
    if not user or not check_password_hash(user.password_hash, data.get("password", "")):
        return jsonify({"error": "Invalid email or password"}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "business_name": user.business_name,
            "onboarding_completed": user.onboarding_completed,
            "sells_meat": user.sells_meat,
            "sells_retail": user.sells_retail,
        }
    }), 200


@auth_bp.route("/onboarding", methods=["POST"])
@jwt_required()
def complete_onboarding():
    """Called after the 'what do you sell?' popup on first login."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    data = request.get_json()
    user.sells_meat = data.get("sells_meat", False)
    user.sells_retail = data.get("sells_retail", False)
    user.onboarding_completed = True

    db.session.commit()
    return jsonify({"message": "Onboarding completed"}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    return jsonify({
        "id": user.id,
        "email": user.email,
        "business_name": user.business_name,
        "business_address": user.business_address,
        "tin": user.tin,
        "vat_status": user.vat_status,
        "sells_meat": user.sells_meat,
        "sells_retail": user.sells_retail,
        "onboarding_completed": user.onboarding_completed,
    }), 200


@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_current_user():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.get_json() or {}

    if "business_name" in data:
        if not data["business_name"]:
            return jsonify({"error": "Business name is required"}), 400
        user.business_name = data["business_name"]

    for field in ["business_address", "tin", "vat_status"]:
        if field in data:
            setattr(user, field, data[field] or None)

    if "vat_status" in data and data["vat_status"] not in ("vat", "non_vat"):
        return jsonify({"error": "vat_status must be 'vat' or 'non_vat'"}), 400

    if "sells_meat" in data or "sells_retail" in data:
        sells_meat = data.get("sells_meat", user.sells_meat)
        sells_retail = data.get("sells_retail", user.sells_retail)
        if not sells_meat and not sells_retail:
            return jsonify({"error": "At least one product type must be selected"}), 400
        user.sells_meat = sells_meat
        user.sells_retail = sells_retail

    db.session.commit()

    return jsonify({
        "id": user.id,
        "email": user.email,
        "business_name": user.business_name,
        "business_address": user.business_address,
        "tin": user.tin,
        "vat_status": user.vat_status,
        "sells_meat": user.sells_meat,
        "sells_retail": user.sells_retail,
        "onboarding_completed": user.onboarding_completed,
    }), 200