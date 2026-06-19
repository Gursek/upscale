from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hmac
import os

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
import requests

from models.db import db
from models.scale_reading import ScaleReading
from models.user import User

scale_bp = Blueprint("scale", __name__)


def _utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_captured_at(value):
    if not value:
        return _utc_now_naive()
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def _scale_max_age_seconds():
    return max(1, int(os.getenv("SCALE_MAX_AGE_SECONDS", "10")))


def _authorized_scale_push():
    configured = os.getenv("SCALE_INGEST_API_KEY", "")
    supplied = request.headers.get("X-Scale-Key", "")
    return bool(configured) and hmac.compare_digest(configured, supplied)


def _configured_scale_user():
    configured_user_id = os.getenv("SCALE_INGEST_USER_ID")
    configured_user_email = os.getenv("SCALE_INGEST_USER_EMAIL")
    if configured_user_id:
        try:
            return db.session.get(User, int(configured_user_id))
        except (TypeError, ValueError):
            return None
    if configured_user_email:
        return User.query.filter_by(email=configured_user_email.strip().lower()).first()
    return None


@scale_bp.route("/readings", methods=["POST"])
def ingest_scale_reading():
    """Receive a stable, calibrated reading pushed outward by the Raspberry Pi."""
    if not _authorized_scale_push():
        return jsonify({"error": "Invalid scale credentials"}), 401

    data = request.get_json(silent=True) or {}
    user = _configured_scale_user()
    has_account_binding = bool(
        os.getenv("SCALE_INGEST_USER_ID") or os.getenv("SCALE_INGEST_USER_EMAIL")
    )
    if (
        os.getenv("FLASK_ENV") == "production"
        and not current_app.config.get("TESTING")
        and not has_account_binding
    ):
        return jsonify({"error": "Scale account binding is not configured"}), 503
    if not has_account_binding and data.get("user_id") is not None:
        try:
            user = db.session.get(User, int(data["user_id"]))
        except (TypeError, ValueError):
            user = None
    elif not has_account_binding and data.get("user_email"):
        user = User.query.filter_by(email=str(data["user_email"]).strip().lower()).first()
    if not user:
        return jsonify({"error": "Scale account was not found"}), 404

    device_id = str(data.get("device_id") or "raspberry-pi").strip()[:100]
    configured_device_id = (os.getenv("SCALE_DEVICE_ID") or "").strip()
    if configured_device_id and not hmac.compare_digest(configured_device_id, device_id):
        return jsonify({"error": "Scale device ID is not authorized"}), 401

    if data.get("stable") is False:
        return jsonify({"error": "Unstable scale readings are not accepted"}), 422

    try:
        weight = Decimal(str(data["weight_kg"])).quantize(Decimal("0.001"))
    except (KeyError, InvalidOperation, TypeError, ValueError):
        return jsonify({"error": "weight_kg must be a valid number"}), 400
    if weight < 0 or weight > Decimal(os.getenv("SCALE_MAX_WEIGHT_KG", "300")):
        return jsonify({"error": "weight_kg is outside the configured scale range"}), 422

    try:
        captured_at = _parse_captured_at(data.get("captured_at"))
    except ValueError:
        return jsonify({"error": "captured_at must be an ISO-8601 datetime"}), 400

    now = _utc_now_naive()
    age_seconds = (now - captured_at).total_seconds()
    if age_seconds > int(os.getenv("SCALE_MAX_INGEST_AGE_SECONDS", "60")):
        return jsonify({"error": "Scale reading is too old"}), 422
    if age_seconds < -30:
        return jsonify({"error": "Scale reading timestamp is in the future"}), 422

    reading = ScaleReading(
        user_id=user.id,
        device_id=device_id,
        weight_kg=weight,
        captured_at=captured_at,
        received_at=now,
    )
    db.session.add(reading)
    db.session.commit()
    return jsonify({
        "accepted": True,
        "reading_id": reading.id,
        "weight_kg": float(reading.weight_kg),
        "captured_at": reading.captured_at.isoformat() + "Z",
    }), 201


@scale_bp.route("/read", methods=["GET"])
@jwt_required()
def read_scale():
    user_id = int(get_jwt_identity())
    reading = ScaleReading.query.filter_by(user_id=user_id).order_by(
        ScaleReading.captured_at.desc(),
        ScaleReading.id.desc(),
    ).first()
    if not reading:
        return jsonify({"error": "No scale reading has been received"}), 503

    age_seconds = max(0, (_utc_now_naive() - reading.captured_at).total_seconds())
    max_age = _scale_max_age_seconds()
    if age_seconds > max_age:
        return jsonify({
            "error": "The latest scale reading is stale",
            "stale": True,
            "age_seconds": round(age_seconds, 1),
            "max_age_seconds": max_age,
        }), 503

    return jsonify({
        "weight_kg": float(reading.weight_kg),
        "captured_at": reading.captured_at.isoformat() + "Z",
        "age_seconds": round(age_seconds, 1),
        "device_id": reading.device_id,
        "stale": False,
    }), 200


@scale_bp.route("/preview", methods=["GET"])
@jwt_required()
def preview_scale():
    scale_service_url = os.getenv("SCALE_SERVICE_URL", "http://localhost:5001")
    try:
        res = requests.get(f"{scale_service_url}/preview", timeout=2)
        return jsonify(res.json()), res.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Scale service not running"}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "Scale service timed out"}), 504


@scale_bp.route("/feed", methods=["GET"])
def scale_feed():
    """Proxy the MJPEG camera feed for the calibration page."""
    scale_service_url = os.getenv("SCALE_SERVICE_URL", "http://localhost:5001")
    try:
        res = requests.get(
            f"{scale_service_url}/feed",
            stream=True,
            timeout=5
        )
        from flask import Response
        return Response(
            res.iter_content(chunk_size=1024),
            content_type=res.headers.get("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        )
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Scale service not running"}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "Scale service timed out"}), 504
