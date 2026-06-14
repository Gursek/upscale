from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from decimal import Decimal
import json

from models.db import db
from models.product import Product
from models.invoice import Invoice, InvoiceItem
from models.user import User
from models.ejournal import EJournalEntry
from models.ejournal import ZReading
from models.audit_log import AuditLog
from services.tax import resolve_tax_classification, compute_invoice_totals

invoices_bp = Blueprint("invoices", __name__)


def _invoice_to_dict(inv: Invoice) -> dict:
    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "invoice_type": inv.invoice_type,
        "date_time": inv.date_time.isoformat(),
        "vatable_sales": float(inv.vatable_sales),
        "vat_amount": float(inv.vat_amount),
        "vat_exempt_sales": float(inv.vat_exempt_sales),
        "zero_rated_sales": float(inv.zero_rated_sales),
        "sspt_sales": float(inv.sspt_sales),
        "percentage_tax_amount": float(inv.percentage_tax_amount),
        "subtotal": float(inv.subtotal),
        "total_amount": float(inv.total_amount),
        "discount_type": inv.discount_type,
        "discount_id_no": inv.discount_id_no,
        "discount_amount": float(inv.discount_amount),
        "status": inv.status,
        "items": [
            {
                "product_id": item.product_id,
                "description": item.description,
                "quantity": float(item.quantity),
                "unit_cost": float(item.unit_cost),
                "line_total": float(item.line_total),
                "tax_line_classification": item.tax_line_classification,
            }
            for item in inv.items
        ],
    }


@invoices_bp.route("/", methods=["POST"])
@jwt_required()
def create_invoice():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    data = request.get_json()

    cart = data.get("items", [])
    if not cart:
        return jsonify({"error": "Cart is empty"}), 400
    
    today = date.today()
    existing_z = ZReading.query.filter_by(user_id=user_id, business_date=today).first()
    if existing_z:
        return jsonify({
            "error": "Z-Reading has already been generated for today. No further transactions can be recorded for this business date.",
            "z_reading_id": existing_z.id,
            "generated_at": existing_z.generated_at.isoformat()
        }), 409

    # --- Step 1: validate stock + resolve line items ---
    line_items = []
    products_to_update = []

    for entry in cart:
        product = Product.query.filter_by(id=entry["product_id"], user_id=user_id, is_archived=False).first()
        if not product:
            return jsonify({"error": f"Product {entry['product_id']} not found"}), 404

        qty = Decimal(str(entry["quantity"]))
        if qty <= 0:
            return jsonify({"error": "Quantity must be greater than zero"}), 400

        if product.stock_quantity < qty:
            return jsonify({
                "error": f"Insufficient stock for {product.name}. Available: {product.stock_quantity}{product.unit}"
            }), 400

        unit_cost = Decimal(str(product.price))
        line_total = (unit_cost * qty).quantize(Decimal("0.01"))
        tax_cls = resolve_tax_classification(product.tax_classification, user.vat_status)

        line_items.append({
            "product_id": product.id,
            "description": product.name + (f" ({product.cut_type})" if product.cut_type else ""),
            "quantity": qty,
            "unit_cost": unit_cost,
            "line_total": line_total,
            "tax_line_classification": tax_cls,
        })
        products_to_update.append((product, qty))

    # --- Step 2: compute totals ---
    totals = compute_invoice_totals(
        [{"line_total": li["line_total"], "tax_line_classification": li["tax_line_classification"]} for li in line_items],
        user.vat_status,
    )

    discount_amount = Decimal(str(data.get("discount_amount", 0)))
    total_amount = totals["total_amount"] - discount_amount

    # --- Step 3: generate sequential invoice number ---
    invoice_number = user.next_invoice_number()

    # --- Step 4: create invoice record ---
    invoice = Invoice(
        user_id=user_id,
        invoice_number=invoice_number,
        invoice_type=data.get("invoice_type", "cash"),
        date_time=datetime.utcnow(),
        vatable_sales=totals["vatable_sales"],
        vat_amount=totals["vat_amount"],
        vat_exempt_sales=totals["vat_exempt_sales"],
        zero_rated_sales=totals["zero_rated_sales"],
        sspt_sales=totals["sspt_sales"],
        percentage_tax_amount=totals["percentage_tax_amount"],
        subtotal=totals["subtotal"],
        total_amount=total_amount,
        discount_type=data.get("discount_type"),
        discount_id_no=data.get("discount_id_no"),
        discount_amount=discount_amount,
        status="active",
    )
    db.session.add(invoice)
    db.session.flush()  # get invoice.id

    # --- Step 5: create invoice items + deduct stock ---
    for li in line_items:
        item = InvoiceItem(
            invoice_id=invoice.id,
            product_id=li["product_id"],
            description=li["description"],
            quantity=li["quantity"],
            unit_cost=li["unit_cost"],
            line_total=li["line_total"],
            tax_line_classification=li["tax_line_classification"],
        )
        db.session.add(item)

    for product, qty in products_to_update:
        before_stock = float(product.stock_quantity)
        product.stock_quantity -= qty

        db.session.add(AuditLog(
            user_id=user_id,
            entity_type="product",
            entity_id=product.id,
            action="sale_deduction",
            before_state=json.dumps({"stock_quantity": before_stock}),
            after_state=json.dumps({"stock_quantity": float(product.stock_quantity)}),
        ))

    db.session.flush()

    # --- Step 6: e-journal entry ---
    db.session.add(EJournalEntry(
        user_id=user_id,
        entry_date=date.today(),
        entry_type="invoice",
        reference_id=invoice.id,
        snapshot_json=json.dumps(_invoice_to_dict(invoice)),
    ))

    db.session.commit()

    return jsonify(_invoice_to_dict(invoice)), 201


@invoices_bp.route("/", methods=["GET"])
@jwt_required()
def list_invoices():
    user_id = int(get_jwt_identity())
    invoices = Invoice.query.filter_by(user_id=user_id).order_by(Invoice.date_time.desc()).all()
    return jsonify([_invoice_to_dict(inv) for inv in invoices]), 200


@invoices_bp.route("/<int:invoice_id>", methods=["GET"])
@jwt_required()
def get_invoice(invoice_id):
    user_id = int(get_jwt_identity())
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user_id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404
    return jsonify(_invoice_to_dict(invoice)), 200


@invoices_bp.route("/<int:invoice_id>/void", methods=["POST"])
@jwt_required()
def void_invoice(invoice_id):
    user_id = int(get_jwt_identity())
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user_id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found"}), 404

    if invoice.status == "voided":
        return jsonify({"error": "Invoice already voided"}), 400

    data = request.get_json() or {}
    reason = data.get("reason", "")

    # Restore stock for each item
    for item in invoice.items:
        if item.product_id:
            product = Product.query.get(item.product_id)
            if product:
                before_stock = float(product.stock_quantity)
                product.stock_quantity += item.quantity
                db.session.add(AuditLog(
                    user_id=user_id,
                    entity_type="product",
                    entity_id=product.id,
                    action="void_restock",
                    before_state=json.dumps({"stock_quantity": before_stock}),
                    after_state=json.dumps({"stock_quantity": float(product.stock_quantity)}),
                ))

    invoice.status = "voided"
    invoice.voided_at = datetime.utcnow()
    invoice.voided_reason = reason

    db.session.add(EJournalEntry(
        user_id=user_id,
        entry_date=date.today(),
        entry_type="void",
        reference_id=invoice.id,
        snapshot_json=json.dumps({"invoice_number": invoice.invoice_number, "reason": reason}),
    ))

    db.session.commit()
    return jsonify({"message": "Invoice voided", "invoice": _invoice_to_dict(invoice)}), 200