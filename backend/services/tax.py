from decimal import Decimal


def resolve_tax_classification(product_tax_class: str, seller_vat_status: str) -> str:
    """
    Determines how a line item's amount should be classified on the invoice,
    based on the product's inherent tax nature and the seller's registration status.
    """
    if product_tax_class == "exempt":
        return "vat_exempt"

    if product_tax_class == "zero_rated":
        return "zero_rated"

    if seller_vat_status == "vat":
        return "vatable"
    else:
        return "sspt"


def compute_invoice_totals(line_items: list[dict], seller_vat_status: str) -> dict:
    """
    line_items: [{ "line_total": Decimal, "tax_line_classification": str }, ...]
    Returns the aggregated breakdown for the Invoice record.
    """
    totals = {
        "vatable_sales": Decimal("0"),
        "vat_amount": Decimal("0"),
        "vat_exempt_sales": Decimal("0"),
        "zero_rated_sales": Decimal("0"),
        "sspt_sales": Decimal("0"),
        "percentage_tax_amount": Decimal("0"),
        "subtotal": Decimal("0"),
    }

    for item in line_items:
        amt = Decimal(str(item["line_total"]))
        cls = item["tax_line_classification"]
        totals["subtotal"] += amt

        if cls == "vatable":
            net = amt / Decimal("1.12")
            vat = amt - net
            totals["vatable_sales"] += net
            totals["vat_amount"] += vat
        elif cls == "vat_exempt":
            totals["vat_exempt_sales"] += amt
        elif cls == "zero_rated":
            totals["zero_rated_sales"] += amt
        elif cls == "sspt":
            totals["sspt_sales"] += amt
            totals["percentage_tax_amount"] += amt * Decimal("0.03")

    totals["total_amount"] = totals["subtotal"]
    return totals