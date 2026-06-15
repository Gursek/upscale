from decimal import Decimal
from datetime import datetime, date

from models.db import db
from models.invoice import Invoice
from models.ejournal import XReading, ZReading
from models.user import User
from services.business_time import business_day_utc_bounds, business_today, utc_now_naive


def _aggregate_invoices(user_id, start_dt, end_dt):
    """Sum up active invoices in the given datetime range."""
    invoices = Invoice.query.filter(
        Invoice.user_id == user_id,
        Invoice.date_time >= start_dt,
        Invoice.date_time < end_dt,
    ).all()

    active = [inv for inv in invoices if inv.status == "active"]
    voided = [inv for inv in invoices if inv.status == "voided"]

    totals = {
        "total_sales": Decimal("0"),
        "vatable_sales": Decimal("0"),
        "vat_exempt_sales": Decimal("0"),
        "zero_rated_sales": Decimal("0"),
        "sspt_sales": Decimal("0"),
        "vat_amount": Decimal("0"),
        "percentage_tax_amount": Decimal("0"),
        "cash_sales": Decimal("0"),
        "transaction_count": len(active),
        "void_count": len(voided),
    }

    for inv in active:
        totals["total_sales"] += inv.total_amount
        totals["vatable_sales"] += inv.vatable_sales
        totals["vat_exempt_sales"] += inv.vat_exempt_sales
        totals["zero_rated_sales"] += inv.zero_rated_sales
        totals["sspt_sales"] += inv.sspt_sales
        totals["vat_amount"] += inv.vat_amount
        totals["percentage_tax_amount"] += inv.percentage_tax_amount
        if inv.payment_mode == "cash":
            totals["cash_sales"] += inv.total_amount

    # invoice number range — across both active and voided (sequence is continuous)
    all_for_numbering = sorted(invoices, key=lambda i: i.invoice_number)
    totals["starting_invoice_no"] = all_for_numbering[0].invoice_number if all_for_numbering else None
    totals["ending_invoice_no"] = all_for_numbering[-1].invoice_number if all_for_numbering else None

    return totals


def generate_x_reading(user_id, shift_date=None):
    """
    Snapshot of sales so far for the given date (default: today).
    Can be generated multiple times per shift — does not close anything.
    """
    if shift_date is None:
        shift_date = business_today(User.query.get(user_id).business_day_cutoff)

    user = User.query.get(user_id)
    start_dt, end_dt = business_day_utc_bounds(shift_date, user.business_day_cutoff)

    totals = _aggregate_invoices(user_id, start_dt, end_dt)

    reading = XReading(
        user_id=user_id,
        shift_date=shift_date,
        generated_at=utc_now_naive(),
        total_sales=totals["total_sales"],
        vatable_sales=totals["vatable_sales"],
        vat_exempt_sales=totals["vat_exempt_sales"],
        zero_rated_sales=totals["zero_rated_sales"],
        vat_amount=totals["vat_amount"],
        transaction_count=totals["transaction_count"],
        void_count=totals["void_count"],
        starting_invoice_no=totals["starting_invoice_no"],
        ending_invoice_no=totals["ending_invoice_no"],
        cash_sales=totals["cash_sales"],
        reset_counter=user.reset_counter or 0,
    )
    db.session.add(reading)
    db.session.flush()
    return reading, totals


def generate_z_reading(user_id, business_date=None):
    """
    End-of-day report. Increments the Z-counter and accumulated grand total.
    Should be generated once per business day, after which no further sales
    for that date should be recorded.
    """
    if business_date is None:
        business_date = business_today(User.query.get(user_id).business_day_cutoff)

    user = User.query.get(user_id)
    start_dt, end_dt = business_day_utc_bounds(business_date, user.business_day_cutoff)

    totals = _aggregate_invoices(user_id, start_dt, end_dt)

    # Get previous Z-reading to compute accumulated grand total + z_counter
    last_z = ZReading.query.filter_by(user_id=user_id).order_by(ZReading.id.desc()).first()
    prev_accumulated = last_z.accumulated_grand_total if last_z else Decimal("0")
    next_z_counter = (last_z.z_counter + 1) if last_z else 1

    accumulated_grand_total = prev_accumulated + totals["total_sales"]

    reading = ZReading(
        user_id=user_id,
        business_date=business_date,
        generated_at=utc_now_naive(),
        total_sales=totals["total_sales"],
        vatable_sales=totals["vatable_sales"],
        vat_exempt_sales=totals["vat_exempt_sales"],
        zero_rated_sales=totals["zero_rated_sales"],
        vat_amount=totals["vat_amount"],
        transaction_count=totals["transaction_count"],
        void_count=totals["void_count"],
        accumulated_grand_total=accumulated_grand_total,
        z_counter=next_z_counter,
        starting_invoice_no=totals["starting_invoice_no"],
        ending_invoice_no=totals["ending_invoice_no"],
        cash_sales=totals["cash_sales"],
        reset_counter=user.reset_counter or 0,
    )
    db.session.add(reading)
    db.session.flush()
    return reading, totals
