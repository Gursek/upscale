import hashlib
import json
from datetime import date, datetime
from decimal import Decimal

from flask import has_request_context, request

from models.audit_log import AuditLog
from models.db import db


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Unsupported audit value: {type(value)!r}")


def canonical_json(value) -> str:
    return json.dumps(
        value,
        default=_json_default,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def add_audit_event(
    *,
    user_id: int,
    entity_type: str,
    entity_id: int,
    action: str,
    actor: str | None = None,
    terminal_id: str | None = None,
    before=None,
    after=None,
) -> AuditLog:
    if actor is None or terminal_id is None:
        from models.user import User

        owner = User.query.get(user_id)
        actor = actor or (owner.email if owner else None)
        terminal_id = terminal_id or (
            owner.machine_identification_number if owner else None
        )
    previous = (
        AuditLog.query.filter(
            AuditLog.user_id == user_id,
            AuditLog.event_hash.isnot(None),
        )
        .order_by(AuditLog.id.desc())
        .with_for_update()
        .first()
    )
    previous_hash = previous.event_hash if previous else None
    created_at = datetime.utcnow()
    payload = {
        "user_id": user_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "actor": actor,
        "terminal_id": terminal_id,
        "before": before,
        "after": after,
        "created_at": created_at,
        "previous_hash": previous_hash,
    }
    event_hash = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    entry = AuditLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        terminal_id=terminal_id,
        ip_address=request.remote_addr if has_request_context() else None,
        before_state=canonical_json(before) if before is not None else None,
        after_state=canonical_json(after) if after is not None else None,
        previous_hash=previous_hash,
        event_hash=event_hash,
        created_at=created_at,
    )
    db.session.add(entry)
    return entry


def seller_snapshot(user) -> dict:
    return {
        "registered_name": user.registered_name or user.business_name,
        "business_name": user.business_name,
        "business_address": user.business_address,
        "tin": user.tin,
        "branch_code": user.branch_code or "00000",
        "vat_status": user.vat_status,
        "machine_identification_number": user.machine_identification_number,
        "machine_serial_number": user.machine_serial_number,
        "software_license_number": user.software_license_number,
        "accreditation_number": user.accreditation_number,
        "accreditation_date_issued": user.accreditation_date_issued,
        "accreditation_valid_until": user.accreditation_valid_until,
        "ptu_number": user.ptu_number,
        "ptu_date_issued": user.ptu_date_issued,
        "accredited_supplier_name": user.accredited_supplier_name,
        "accredited_supplier_address": user.accredited_supplier_address,
        "accredited_supplier_tin": user.accredited_supplier_tin,
        "software_version": user.software_version,
        "reset_counter": user.reset_counter or 0,
    }


def compliance_readiness(user) -> dict:
    required = {
        "registered_name": user.registered_name,
        "business_name": user.business_name,
        "business_address": user.business_address,
        "tin": user.tin,
        "branch_code": user.branch_code,
        "machine_identification_number": user.machine_identification_number,
        "machine_serial_or_license": (
            user.machine_serial_number or user.software_license_number
        ),
        "accreditation_number": user.accreditation_number,
        "accreditation_date_issued": user.accreditation_date_issued,
        "accreditation_valid_until": user.accreditation_valid_until,
        "ptu_number": user.ptu_number,
        "ptu_date_issued": user.ptu_date_issued,
        "accredited_supplier_name": user.accredited_supplier_name,
        "accredited_supplier_address": user.accredited_supplier_address,
        "accredited_supplier_tin": user.accredited_supplier_tin,
        "software_version": user.software_version,
    }
    missing = [name for name, value in required.items() if not value]
    return {
        "ready": not missing,
        "missing_fields": missing,
        "status": "registration_complete" if not missing else "configuration_incomplete",
    }
