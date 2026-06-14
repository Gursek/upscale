from datetime import datetime
from models.db import db

class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(150), nullable=False)
    contact_info = db.Column(db.String(255))
    products_supplied = db.Column(db.Text)  # free-text or comma-separated for now

    is_archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)