from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import os
import random
import smtplib
from email.message import EmailMessage
from models.db import db
from models.user import User
from services.compliance import add_audit_event, compliance_readiness

auth_bp = Blueprint("auth", __name__)

COMPLIANCE_FIELDS = (
    "branch_code",
    "registered_name",
    "machine_identification_number",
    "machine_serial_number",
    "software_license_number",
    "accreditation_number",
    "ptu_number",
    "accredited_supplier_name",
    "accredited_supplier_address",
    "accredited_supplier_tin",
    "software_version",
        "business_day_cutoff",
)
DATE_FIELDS = (
    "accreditation_date_issued",
    "accreditation_valid_until",
    "ptu_date_issued",
)


def _user_to_dict(user):
    result = {
        "id": user.id,
        "email": user.email,
        "business_name": user.business_name,
        "registered_name": user.registered_name,
        "business_address": user.business_address,
        "tin": user.tin,
        "vat_status": user.vat_status,
        "sells_meat": user.sells_meat,
        "sells_fish": user.sells_fish,
        "sells_retail": user.sells_retail,
        "sells_veggies": user.sells_veggies,
        "onboarding_completed": user.onboarding_completed,
        "reset_counter": user.reset_counter or 0,
    }
    for field in COMPLIANCE_FIELDS:
        result[field] = getattr(user, field)
    for field in DATE_FIELDS:
        value = getattr(user, field)
        result[field] = value.isoformat() if value else None
    result["compliance"] = compliance_readiness(user)
    return result

def _password_errors(password):
    password = password or ""
    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not any(char.isupper() for char in password):
        errors.append("one uppercase letter")
    if not any(char.isdigit() for char in password):
        errors.append("one number")
    if not any(not char.isalnum() for char in password):
        errors.append("one special character")
    return errors


def _send_password_reset_email(to_email: str, otp: str) -> bool:
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM") or username
    port = int(os.getenv("SMTP_PORT", "587"))
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if not host or not username or not password or not sender:
        return False

    message = EmailMessage()
    message["Subject"] = "Your UpScale POS password reset code"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        "Use this one-time code to reset your UpScale POS password.\n\n"
        f"Code: {otp}\n\n"
        "This code expires in 10 minutes. If you did not request this, you can ignore this email."
    )

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        if use_tls:
            smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)
    return True


@auth_bp.route("/password-reset/request", methods=["POST"])
def request_password_reset():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "If the email exists, a reset code has been sent."}), 200

    otp = f"{random.SystemRandom().randint(0, 999999):06d}"
    user.password_reset_otp_hash = generate_password_hash(otp)
    user.password_reset_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()

    try:
        sent = _send_password_reset_email(user.email, otp)
    except Exception:
        sent = False

    if not sent:
        return jsonify({"error": "Password reset email is not configured. Contact the system administrator."}), 503

    return jsonify({"message": "If the email exists, a reset code has been sent."}), 200


@auth_bp.route("/password-reset/confirm", methods=["POST"])
def confirm_password_reset():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()
    new_password = data.get("new_password") or ""

    if not email or not otp or not new_password:
        return jsonify({"error": "Email, code, and new password are required"}), 400

    password_errors = _password_errors(new_password)
    if password_errors:
        return jsonify({"error": f"New password must include {', '.join(password_errors)}"}), 400

    user = User.query.filter_by(email=email).first()
    if (
        not user
        or not user.password_reset_otp_hash
        or not user.password_reset_expires_at
        or user.password_reset_expires_at < datetime.utcnow()
        or not check_password_hash(user.password_reset_otp_hash, otp)
    ):
        return jsonify({"error": "Invalid or expired reset code"}), 400

    user.password_hash = generate_password_hash(new_password)
    user.password_reset_otp_hash = None
    user.password_reset_expires_at = None
    add_audit_event(
        user_id=user.id,
        entity_type="security",
        entity_id=user.id,
        action="password_reset",
        actor=user.email,
        after={"reset": True},
    )
    db.session.commit()
    return jsonify({"message": "Password reset successful"}), 200


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    required = ["email", "password", "business_name"]
    if not all(field in data and data[field] for field in required):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    password_errors = _password_errors(data["password"])
    if password_errors:
        return jsonify({
            "error": f"Password must include {', '.join(password_errors)}"
        }), 400

    user = User(
        email=data["email"],
        password_hash=generate_password_hash(data["password"]),
        business_name=data["business_name"],
        registered_name=data.get("registered_name") or data["business_name"],
        business_address=data.get("business_address"),
        tin=data.get("tin"),
        vat_status=data.get("vat_status", "non_vat"),
    )
    db.session.add(user)
    db.session.flush()
    add_audit_event(
        user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        action="register",
        actor=user.email,
        after={"email": user.email, "business_name": user.business_name},
    )
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    add_audit_event(
        user_id=user.id,
        entity_type="session",
        entity_id=user.id,
        action="login",
        actor=user.email,
        terminal_id=user.machine_identification_number,
        after={"result": "success"},
    )
    db.session.commit()
    return jsonify({
        "access_token": access_token,
        "user": _user_to_dict(user)
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    user = User.query.filter_by(email=data.get("email")).first()
    if not user or not check_password_hash(user.password_hash, data.get("password", "")):
        return jsonify({"error": "Invalid email or password"}), 401

    access_token = create_access_token(identity=str(user.id))
    add_audit_event(
        user_id=user.id,
        entity_type="session",
        entity_id=user.id,
        action="login",
        actor=user.email,
        terminal_id=user.machine_identification_number,
        after={"result": "success"},
    )
    db.session.commit()
    return jsonify({
        "access_token": access_token,
        "user": _user_to_dict(user)
    }), 200


@auth_bp.route("/onboarding", methods=["POST"])
@jwt_required()
def complete_onboarding():
    """Called after the 'what do you sell?' popup on first login."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    data = request.get_json() or {}
    user.sells_meat = data.get("sells_meat", False)
    user.sells_fish = data.get("sells_fish", False)
    user.sells_retail = data.get("sells_retail", False)
    user.sells_veggies = data.get("sells_veggies", False)
    if not any((user.sells_meat, user.sells_fish, user.sells_retail, user.sells_veggies)):
        return jsonify({"error": "Select at least one product type"}), 400
    user.onboarding_completed = True

    add_audit_event(
        user_id=user.id,
        entity_type="settings",
        entity_id=user.id,
        action="onboarding",
        actor=user.email,
        after={
            "sells_meat": user.sells_meat,
            "sells_fish": user.sells_fish,
            "sells_retail": user.sells_retail,
            "sells_veggies": user.sells_veggies,
        },
    )
    db.session.commit()
    return jsonify({"message": "Onboarding completed"}), 200


@auth_bp.route("/verify-password", methods=["POST"])
@jwt_required()
def verify_password():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.get_json() or {}

    if not user or not check_password_hash(user.password_hash, data.get("password", "")):
        return jsonify({"error": "Incorrect password"}), 401

    return jsonify({"valid": True}), 200


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.get_json() or {}

    if not user or not check_password_hash(user.password_hash, data.get("current_password", "")):
        return jsonify({"error": "Current password is incorrect"}), 401

    new_password = data.get("new_password", "")
    password_errors = _password_errors(new_password)
    if password_errors:
        return jsonify({
            "error": f"New password must include {', '.join(password_errors)}"
        }), 400

    if check_password_hash(user.password_hash, new_password):
        return jsonify({"error": "New password must be different from the current password"}), 400

    user.password_hash = generate_password_hash(new_password)
    add_audit_event(
        user_id=user.id,
        entity_type="security",
        entity_id=user.id,
        action="change_password",
        actor=user.email,
        terminal_id=user.machine_identification_number,
        after={"changed": True},
    )
    db.session.commit()
    return jsonify({"message": "Password changed"}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    return jsonify(_user_to_dict(user)), 200


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

    before = _user_to_dict(user)

    for field in ["business_address", "tin", "vat_status", *COMPLIANCE_FIELDS]:
        if field in data:
            setattr(user, field, data[field] or None)

    for field in DATE_FIELDS:
        if field in data:
            try:
                setattr(
                    user,
                    field,
                    datetime.strptime(data[field], "%Y-%m-%d").date()
                    if data[field]
                    else None,
                )
            except (TypeError, ValueError):
                return jsonify({"error": f"{field} must use YYYY-MM-DD format"}), 400

    if "vat_status" in data and data["vat_status"] not in ("vat", "non_vat"):
        return jsonify({"error": "vat_status must be 'vat' or 'non_vat'"}), 400
    if user.branch_code and (not user.branch_code.isdigit() or len(user.branch_code) != 5):
        return jsonify({"error": "branch_code must contain exactly 5 digits"}), 400
    if user.business_day_cutoff:
        try:
            datetime.strptime(user.business_day_cutoff, "%H:%M")
        except ValueError:
            return jsonify({"error": "business_day_cutoff must use HH:MM format"}), 400

    if any(field in data for field in ("sells_meat", "sells_fish", "sells_retail", "sells_veggies")):
        sells_meat = data.get("sells_meat", user.sells_meat)
        sells_fish = data.get("sells_fish", user.sells_fish)
        sells_retail = data.get("sells_retail", user.sells_retail)
        sells_veggies = data.get("sells_veggies", user.sells_veggies)
        if not any((sells_meat, sells_fish, sells_retail, sells_veggies)):
            return jsonify({"error": "At least one product type must be selected"}), 400
        user.sells_meat = sells_meat
        user.sells_fish = sells_fish
        user.sells_retail = sells_retail
        user.sells_veggies = sells_veggies

    after = _user_to_dict(user)
    add_audit_event(
        user_id=user.id,
        entity_type="settings",
        entity_id=user.id,
        action="update",
        actor=user.email,
        terminal_id=user.machine_identification_number,
        before=before,
        after=after,
    )
    db.session.commit()

    return jsonify(_user_to_dict(user)), 200
