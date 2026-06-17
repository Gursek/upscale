from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from models.invoice import Invoice
from models.product import Product
from models.user import User
from services.business_time import (
    PHILIPPINE_TZ,
    business_day_utc_bounds,
    business_now,
    business_today,
    local_interval_to_utc,
    to_business_iso,
)


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/", methods=["GET"])
@jwt_required()
def get_dashboard():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    today = business_today(user.business_day_cutoff)
    start_today, end_today = business_day_utc_bounds(today, user.business_day_cutoff)

    today_invoices = Invoice.query.filter(
        Invoice.user_id == user_id,
        Invoice.status == "active",
        Invoice.date_time >= start_today,
        Invoice.date_time <= end_today,
    ).all()
    today_sales = sum((invoice.total_amount for invoice in today_invoices), Decimal("0"))

    low_stock_products = Product.query.filter(
        Product.user_id == user_id,
        Product.is_archived.is_(False),
        Product.is_active.is_(True),
        Product.low_stock_threshold > 0,
        Product.stock_quantity <= Product.low_stock_threshold,
    ).order_by(Product.stock_quantity.asc()).limit(10).all()

    recent_invoices = Invoice.query.filter_by(user_id=user_id).order_by(
        Invoice.date_time.desc()
    ).limit(10).all()

    range_name = request.args.get("range", "days")
    chart = []
    if range_name == "hours":
        current_hour = business_now().replace(minute=0, second=0, microsecond=0)
        buckets = [
            (current_hour - timedelta(hours=offset), timedelta(hours=1), "%H:00")
            for offset in range(11, -1, -1)
        ]
    elif range_name == "months":
        buckets = []
        cursor = today.replace(day=1)
        for offset in range(11, -1, -1):
            month_index = cursor.year * 12 + cursor.month - 1 - offset
            month_start = date(month_index // 12, month_index % 12 + 1, 1)
            next_index = month_index + 1
            next_month = date(next_index // 12, next_index % 12 + 1, 1)
            buckets.append((
                datetime.combine(month_start, datetime.min.time(), tzinfo=PHILIPPINE_TZ),
                datetime.combine(next_month, datetime.min.time(), tzinfo=PHILIPPINE_TZ) - datetime.combine(month_start, datetime.min.time(), tzinfo=PHILIPPINE_TZ),
                "%b %Y",
            ))
    else:
        range_name = "days"
        buckets = [
            (
                datetime.combine(today - timedelta(days=offset), datetime.min.time(), tzinfo=PHILIPPINE_TZ),
                timedelta(days=1),
                "%a",
            )
            for offset in range(6, -1, -1)
        ]

    for bucket_start, duration, label_format in buckets:
        bucket_end = bucket_start + duration
        query_start, query_end = local_interval_to_utc(bucket_start, bucket_end)
        total = sum((
            invoice.total_amount for invoice in Invoice.query.filter(
                Invoice.user_id == user_id,
                Invoice.status == "active",
                Invoice.date_time >= query_start,
                Invoice.date_time < query_end,
            ).all()
        ), Decimal("0"))
        chart.append({
            "label": bucket_start.strftime(label_format),
            "start": bucket_start.strftime("%Y-%m-%d %H:%M:%S"),
            "total": float(total),
        })

    return jsonify({
        "today_sales": float(today_sales),
        "transaction_count": len(today_invoices),
        "low_stock_count": len(low_stock_products),
        "sync_status": "not_configured",
        "recent_transactions": [
            {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "date_time": to_business_iso(invoice.date_time),
                "total_amount": float(invoice.total_amount),
                "status": invoice.status,
            }
            for invoice in recent_invoices
        ],
        "low_stock_products": [
            {
                "id": product.id,
                "name": product.name,
                "stock_quantity": float(product.stock_quantity),
                "low_stock_threshold": float(product.low_stock_threshold),
                "unit": product.unit,
            }
            for product in low_stock_products
        ],
        "sales_range": range_name,
        "sales_series": chart,
    }), 200
