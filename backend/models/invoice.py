from datetime import datetime
from models.db import db

class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    invoice_number = db.Column(db.String(6), nullable=False)
    invoice_type = db.Column(db.String(10), default="cash")  # 'cash' or 'charge'
    date_time = db.Column(db.DateTime, default=datetime.utcnow)

    # Full sales breakdown — populated based on user's vat_status at time of sale
    vatable_sales = db.Column(db.Numeric(10, 2), default=0)      # VAT-registered: 12% VAT applies
    vat_amount = db.Column(db.Numeric(10, 2), default=0)          # 12% of vatable_sales
    vat_exempt_sales = db.Column(db.Numeric(10, 2), default=0)    # exempt goods (e.g. meat) regardless of seller's VAT status
    zero_rated_sales = db.Column(db.Numeric(10, 2), default=0)    # rare for retail/meatshop, but kept for completeness

    sspt_sales = db.Column(db.Numeric(10, 2), default=0)          # Non-VAT seller: subject to 3% percentage tax
    percentage_tax_amount = db.Column(db.Numeric(10, 2), default=0)

    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)

    discount_type = db.Column(db.String(20))
    discount_id_no = db.Column(db.String(50))
    discount_amount = db.Column(db.Numeric(10, 2), default=0)

    status = db.Column(db.String(10), default="active")
    voided_at = db.Column(db.DateTime)
    voided_reason = db.Column(db.Text)

    synced = db.Column(db.Boolean, default=False)

    items = db.relationship("InvoiceItem", backref="invoice", lazy=True)


class InvoiceItem(db.Model):
    __tablename__ = "invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))

    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)

    # Resolved at time of sale based on product.tax_classification + seller's vat_status
    tax_line_classification = db.Column(db.String(15), nullable=False)
    # possible values: 'vatable', 'vat_exempt', 'zero_rated', 'sspt'