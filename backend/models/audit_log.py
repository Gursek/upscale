from datetime import datetime
from models.db import db

class AuditLog(db.Model):
    """
    Powers archive/restore traceability. Every mutating action writes a row here
    with a full before-state snapshot.
    """
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    entity_type = db.Column(db.String(30), nullable=False)  # 'product','supplier','invoice', etc.
    entity_id = db.Column(db.Integer, nullable=False)

    action = db.Column(db.String(20), nullable=False)  # 'create','update','archive','restore','void'
    before_state = db.Column(db.Text)  # JSON snapshot
    after_state = db.Column(db.Text)   # JSON snapshot

    reverted = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)