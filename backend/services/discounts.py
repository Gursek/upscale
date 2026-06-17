from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value or "0")).quantize(CENT, rounding=ROUND_HALF_UP)


def normalize_discount_type(discount_type: str | None) -> str | None:
    if not discount_type:
        return None

    normalized = str(discount_type).strip().lower().replace("-", "_")
    aliases = {
        "sc": "senior_citizen",
        "senior": "senior_citizen",
        "senior_citizen": "senior_citizen",
        "pwd": "pwd",
        "naac": "naac",
        "national_athletes": "naac",
        "national_athlete": "naac",
        "solo_parent": "solo_parent",
    }
    return aliases.get(normalized)


def compute_statutory_discount(discount_type, subtotal, vatable_sales, vat_amount) -> dict:
    """
    Computes statutory discounts server-side using Decimal math.

    SC/PWD: 20% of VAT-exclusive amount plus VAT deduction.
    NAAC: 20% discount, no VAT deduction.
    SOLO_PARENT: 10% discount, no VAT deduction.
    """
    normalized = normalize_discount_type(discount_type)
    subtotal = _money(subtotal)
    vat_amount = _money(vat_amount)
    vatable_sales = _money(vatable_sales)

    if not normalized:
        return {
            "discount_type": None,
            "discount_amount": Decimal("0.00"),
            "vat_deduction": Decimal("0.00"),
            "total_deduction": Decimal("0.00"),
            "discountable_base": Decimal("0.00"),
        }

    if normalized in {"senior_citizen", "pwd"}:
        discountable_base = max(subtotal - vat_amount, Decimal("0.00"))
        discount_amount = _money(discountable_base * Decimal("0.20"))
        vat_deduction = vat_amount
    elif normalized == "naac":
        discountable_base = subtotal
        discount_amount = _money(discountable_base * Decimal("0.20"))
        vat_deduction = Decimal("0.00")
    elif normalized == "solo_parent":
        discountable_base = subtotal
        discount_amount = _money(discountable_base * Decimal("0.10"))
        vat_deduction = Decimal("0.00")
    else:
        raise ValueError("Invalid statutory discount type")

    total_deduction = _money(discount_amount + vat_deduction)
    return {
        "discount_type": normalized,
        "discount_amount": discount_amount,
        "vat_deduction": vat_deduction,
        "total_deduction": total_deduction,
        "discountable_base": discountable_base,
    }
