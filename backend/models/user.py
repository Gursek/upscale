from datetime import datetime
from models.db import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    business_name = db.Column(db.String(150), nullable=False)
    business_address = db.Column(db.String(255))
    tin = db.Column(db.String(20))  # Taxpayer Identification Number

    # Drives tax_resolver: 'vat' or 'non_vat'
    vat_status = db.Column(db.String(10), default="non_vat")

    # Onboarding preferences
    sells_meat = db.Column(db.Boolean, default=False)
    sells_retail = db.Column(db.Boolean, default=False)
    onboarding_completed = db.Column(db.Boolean, default=False)

    # Sequential invoice numbering per BIR requirements
    last_invoice_number = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def next_invoice_number(self):
        """Returns zero-padded 6-digit invoice number and increments counter."""
        self.last_invoice_number += 1
        return str(self.last_invoice_number).zfill(6)