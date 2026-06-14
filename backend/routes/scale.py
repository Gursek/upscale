from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

scale_bp = Blueprint("scale", __name__)

@scale_bp.route("/read", methods=["GET"])
@jwt_required()
def read_scale():
    """
    Placeholder — returns mock weight.
    Will be replaced with OpenCV OCR reading from scale_service.py.
    """
    return jsonify({
        "weight_kg": 0.700,
        "weight_g": 700,
        "source": "mock"
    }), 200