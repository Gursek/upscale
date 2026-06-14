from flask import Blueprint

inventory_bp = Blueprint("inventory", __name__)

@inventory_bp.route("/", methods=["GET"])
def list_products():
    return {"message": "inventory endpoint"}