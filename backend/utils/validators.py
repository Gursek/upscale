from decimal import Decimal, InvalidOperation


ALLOWED_PRODUCT_CATEGORIES = {"beef", "pork", "chicken", "retail"}
ALLOWED_PRICING_TYPES = {"per_kg", "fixed"}
ALLOWED_TAX_CLASSIFICATIONS = {"exempt", "standard"}
ALLOWED_PRODUCT_UNITS = {"kg", "pcs", "pack", "box", "bottle", "sachet"}


def _decimal_field(data, field, *, required=False, positive=False, non_negative=False, integer=False):
    if field not in data:
        if required:
            raise ValueError(f"{field}: is required")
        return None
    if data[field] in (None, ""):
        raise ValueError(f"{field}: must be numeric")

    try:
        value = Decimal(str(data[field]))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field}: must be numeric")

    if positive and value <= 0:
        raise ValueError(f"{field}: must be greater than zero")
    if non_negative and value < 0:
        raise ValueError(f"{field}: must be non-negative")
    if integer and value != value.to_integral_value():
        raise ValueError(f"{field}: must be a non-negative integer")
    return value


def validate_product_payload(data, *, partial=False):
    data = dict(data or {})
    validated = {}

    if not partial:
        for field in ("name", "category", "pricing_type", "price"):
            if field not in data or data[field] in (None, ""):
                raise ValueError(f"{field}: is required")

    if "category" in data:
        if data["category"] not in ALLOWED_PRODUCT_CATEGORIES:
            raise ValueError("category: must be one of beef, pork, chicken, retail")
        validated["category"] = data["category"]

    if "pricing_type" in data:
        if data["pricing_type"] not in ALLOWED_PRICING_TYPES:
            raise ValueError("pricing_type: must be one of per_kg, fixed")
        validated["pricing_type"] = data["pricing_type"]

    if "tax_classification" in data:
        if data["tax_classification"] not in ALLOWED_TAX_CLASSIFICATIONS:
            raise ValueError("tax_classification: must be one of exempt, standard")
        validated["tax_classification"] = data["tax_classification"]

    if "unit" in data:
        if data["unit"] not in ALLOWED_PRODUCT_UNITS:
            raise ValueError("unit: must be one of kg, pcs, pack, box, bottle, sachet")
        validated["unit"] = data["unit"]

    price = _decimal_field(data, "price", required=not partial, positive=True)
    if price is not None:
        validated["price"] = price

    if not partial:
        stock_quantity = _decimal_field(data, "stock_quantity", non_negative=True)
        if stock_quantity is not None:
            validated["stock_quantity"] = stock_quantity

    low_stock_threshold = _decimal_field(data, "low_stock_threshold", non_negative=True, integer=True)
    if low_stock_threshold is not None:
        validated["low_stock_threshold"] = low_stock_threshold

    return validated
