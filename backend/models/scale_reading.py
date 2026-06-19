from datetime import datetime

from models.db import db


class ScaleReading(db.Model):
    __tablename__ = "scale_readings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    device_id = db.Column(db.String(100), nullable=False, default="raspberry-pi")
    weight_kg = db.Column(db.Numeric(10, 3), nullable=False)
    captured_at = db.Column(db.DateTime, nullable=False, index=True)
    received_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

