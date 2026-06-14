from flask import Blueprint

scale_bp = Blueprint("scale", __name__)

@scale_bp.route("/", methods=["GET"])
def list_products():
    return {"message": "scale endpoint"}