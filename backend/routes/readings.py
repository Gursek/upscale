from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date, datetime
import json

from models.db import db
from models.ejournal import EJournalEntry, XReading, ZReading
from services.readings import generate_x_reading, generate_z_reading

readings_bp = Blueprint("readings", __name__)


def _x_to_dict(r: XReading) -> dict:
    return {
        "id": r.id,
        "shift_date": r.shift_date.isoformat(),
        "generated_at": r.generated_at.isoformat(),
        "total_sales": float(r.total_sales),
        "vatable_sales": float(r.vatable_sales),
        "vat_exempt_sales": float(r.vat_exempt_sales),
        "zero_rated_sales": float(r.zero_rated_sales),
        "vat_amount": float(r.vat_amount),
        "transaction_count": r.transaction_count,
        "void_count": r.void_count,
        "starting_invoice_no": r.starting_invoice_no,
        "ending_invoice_no": r.ending_invoice_no,
    }


def _z_to_dict(r: ZReading) -> dict:
    return {
        "id": r.id,
        "business_date": r.business_date.isoformat(),
        "generated_at": r.generated_at.isoformat(),
        "total_sales": float(r.total_sales),
        "vatable_sales": float(r.vatable_sales),
        "vat_exempt_sales": float(r.vat_exempt_sales),
        "zero_rated_sales": float(r.zero_rated_sales),
        "vat_amount": float(r.vat_amount),
        "transaction_count": r.transaction_count,
        "void_count": r.void_count,
        "accumulated_grand_total": float(r.accumulated_grand_total),
        "z_counter": r.z_counter,
        "starting_invoice_no": r.starting_invoice_no,
        "ending_invoice_no": r.ending_invoice_no,
    }


@readings_bp.route("/x", methods=["POST"])
@jwt_required()
def create_x_reading():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    shift_date = date.today()
    if data.get("date"):
        shift_date = datetime.strptime(data["date"], "%Y-%m-%d").date()

    reading, _ = generate_x_reading(user_id, shift_date)

    db.session.add(EJournalEntry(
        user_id=user_id,
        entry_date=date.today(),
        entry_type="x_reading",
        reference_id=reading.id,
        snapshot_json=json.dumps(_x_to_dict(reading)),
    ))
    db.session.commit()

    return jsonify(_x_to_dict(reading)), 201


@readings_bp.route("/z", methods=["POST"])
@jwt_required()
def create_z_reading():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    business_date = date.today()
    if data.get("date"):
        business_date = datetime.strptime(data["date"], "%Y-%m-%d").date()

    # Prevent duplicate Z-reading for the same business date
    existing = ZReading.query.filter_by(user_id=user_id, business_date=business_date).first()
    if existing:
        return jsonify({"error": f"Z-Reading already generated for {business_date}"}), 409

    reading, _ = generate_z_reading(user_id, business_date)

    db.session.add(EJournalEntry(
        user_id=user_id,
        entry_date=date.today(),
        entry_type="z_reading",
        reference_id=reading.id,
        snapshot_json=json.dumps(_z_to_dict(reading)),
    ))
    db.session.commit()

    return jsonify(_z_to_dict(reading)), 201


@readings_bp.route("/x", methods=["GET"])
@jwt_required()
def list_x_readings():
    user_id = int(get_jwt_identity())
    readings = XReading.query.filter_by(user_id=user_id).order_by(XReading.generated_at.desc()).all()
    return jsonify([_x_to_dict(r) for r in readings]), 200


@readings_bp.route("/z", methods=["GET"])
@jwt_required()
def list_z_readings():
    user_id = int(get_jwt_identity())
    readings = ZReading.query.filter_by(user_id=user_id).order_by(ZReading.generated_at.desc()).all()
    return jsonify([_z_to_dict(r) for r in readings]), 200