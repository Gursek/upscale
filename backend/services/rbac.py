from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from models.user import User


VALID_ROLES = {"owner", "manager", "cashier", "auditor"}


def current_user_role() -> str | None:
    identity = get_jwt_identity()
    if identity is None:
        return None
    user = User.query.get(int(identity))
    if not user:
        return None
    return user.role or "owner"


def roles_required(*allowed_roles: str):
    allowed = set(allowed_roles)

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = current_user_role()
            if role not in allowed:
                return jsonify({"error": "Insufficient permissions"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
