from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
import requests

scale_bp = Blueprint("scale", __name__)

SCALE_SERVICE_URL = "http://localhost:5001"


@scale_bp.route("/read", methods=["GET"])
@jwt_required()
def read_scale():
    try:
        res = requests.get(f"{SCALE_SERVICE_URL}/read", timeout=2)
        data = res.json()
        return jsonify(data), res.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Scale service not running"}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "Scale service timed out"}), 504


@scale_bp.route("/preview", methods=["GET"])
@jwt_required()
def preview_scale():
    try:
        res = requests.get(f"{SCALE_SERVICE_URL}/preview", timeout=2)
        return jsonify(res.json()), res.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Scale service not running"}), 503


@scale_bp.route("/feed", methods=["GET"])
def scale_feed():
    """Proxy the MJPEG camera feed for the calibration page."""
    try:
        res = requests.get(
            f"{SCALE_SERVICE_URL}/feed",
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