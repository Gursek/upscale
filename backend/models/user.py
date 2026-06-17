from datetime import datetime
from models.db import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="owner")

    business_name = db.Column(db.String(150), nullable=False)
    registered_name = db.Column(db.String(150))
    business_address = db.Column(db.String(255))
    tin = db.Column(db.String(20))  # Taxpayer Identification Number
    branch_code = db.Column(db.String(5), default="00000")

    # BIR accreditation and registered POS identity.
    machine_identification_number = db.Column(db.String(50))
    machine_serial_number = db.Column(db.String(100))
    software_license_number = db.Column(db.String(100))
    accreditation_number = db.Column(db.String(100))
    accreditation_date_issued = db.Column(db.Date)
    accreditation_valid_until = db.Column(db.Date)
    ptu_number = db.Column(db.String(100))
    ptu_date_issued = db.Column(db.Date)
    accredited_supplier_name = db.Column(db.String(150))
    accredited_supplier_address = db.Column(db.String(255))
    accredited_supplier_tin = db.Column(db.String(20))
    software_version = db.Column(db.String(50), default="1.0.0")
    reset_counter = db.Column(db.Integer, default=0)
    business_day_cutoff = db.Column(db.String(5), default="00:00")

    # Drives tax_resolver: 'vat' or 'non_vat'
    vat_status = db.Column(db.String(10), default="non_vat")

    # Onboarding preferences
    sells_meat = db.Column(db.Boolean, default=False)
    sells_fish = db.Column(db.Boolean, default=False)
    sells_retail = db.Column(db.Boolean, default=False)
    sells_veggies = db.Column(db.Boolean, default=False)
    onboarding_completed = db.Column(db.Boolean, default=False)

    # Sequential invoice numbering per BIR requirements
    last_invoice_number = db.Column(db.Integer, default=0)

    password_reset_otp_hash = db.Column(db.String(255))
    password_reset_expires_at = db.Column(db.DateTime)
    tokens_revoked_before = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def next_invoice_number(self):
        """Returns zero-padded 6-digit invoice number and increments counter."""
        if self.last_invoice_number >= 999999:
            self.last_invoice_number = 0
            self.reset_counter = (self.reset_counter or 0) + 1
        self.last_invoice_number += 1
        return str(self.last_invoice_number).zfill(6)
