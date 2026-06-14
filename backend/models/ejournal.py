from datetime import datetime
from models.db import db

class EJournalEntry(db.Model):
    """
    Daily electronic journal — required under RMO 24-2023.
    One row per invoice/void/X-reading/Z-reading event.
    Exportable as a daily .txt file per BIR requirements.
    """
    __tablename__ = "e_journal"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    entry_date = db.Column(db.Date, nullable=False)
    entry_type = db.Column(db.String(20), nullable=False)  # 'invoice','void','x_reading','z_reading','adjustment'
    reference_id = db.Column(db.Integer)  # invoice_id or reading_id

    snapshot_json = db.Column(db.Text, nullable=False)  # full record at time of entry
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class XReading(db.Model):
    __tablename__ = "x_readings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    shift_date = db.Column(db.Date, nullable=False)

    total_sales = db.Column(db.Numeric(10, 2), default=0)
    vatable_sales = db.Column(db.Numeric(10, 2), default=0)
    vat_exempt_sales = db.Column(db.Numeric(10, 2), default=0)
    zero_rated_sales = db.Column(db.Numeric(10, 2), default=0)
    vat_amount = db.Column(db.Numeric(10, 2), default=0)

    transaction_count = db.Column(db.Integer, default=0)
    void_count = db.Column(db.Integer, default=0)

    starting_invoice_no = db.Column(db.String(6))
    ending_invoice_no = db.Column(db.String(6))


class ZReading(db.Model):
    __tablename__ = "z_readings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    business_date = db.Column(db.Date, nullable=False)

    total_sales = db.Column(db.Numeric(10, 2), default=0)
    vatable_sales = db.Column(db.Numeric(10, 2), default=0)
    vat_exempt_sales = db.Column(db.Numeric(10, 2), default=0)
    zero_rated_sales = db.Column(db.Numeric(10, 2), default=0)
    vat_amount = db.Column(db.Numeric(10, 2), default=0)

    transaction_count = db.Column(db.Integer, default=0)
    void_count = db.Column(db.Integer, default=0)

    accumulated_grand_total = db.Column(db.Numeric(14, 2), default=0)  # 12-digit min per RMO 24-2023
    z_counter = db.Column(db.Integer, default=1)  # increments each Z-reading generated

    starting_invoice_no = db.Column(db.String(6))
    ending_invoice_no = db.Column(db.String(6))