from datetime import datetime
from models.db import db

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(20), nullable=False)  # 'beef','pork','chicken','retail'
    cut_type = db.Column(db.String(100))  # e.g. 'Ribeye', null for retail

    pricing_type = db.Column(db.String(10), nullable=False)  # 'per_kg' or 'fixed'
    price = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(10), default="kg")  # 'kg' or 'pcs'

    sku = db.Column(db.String(50))  # for retail
    stock_quantity = db.Column(db.Numeric(10, 3), default=0)
    low_stock_threshold = db.Column(db.Numeric(10, 3), default=0)

    tax_classification = db.Column(db.String(15), default="exempt")  # 'vatable','exempt','zero_rated'

    image_url = db.Column(db.String(255))

    is_active = db.Column(db.Boolean, default=True)
    is_archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)