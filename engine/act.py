"""
ACT stage.

Turns a decision into a concrete, draftable artifact — here, a
purchase-order draft with a total cost — rather than leaving the
recommendation as an abstract number. This is the artifact a planner
actually reviews and approves.
"""


def draft_po(feature_row: dict, decision: dict) -> dict:
    qty = decision["recommended_qty"]
    unit_cost = feature_row["unit_cost"]

    return {
        "sku_id": decision["sku_id"],
        "sku_name": decision["sku_name"],
        "category": feature_row["category"],
        "supplier_id": feature_row["supplier_id"],
        "recommended_qty": qty,
        "unit_cost": unit_cost,
        "total_cost": round(qty * unit_cost, 2),
        "confidence": decision["confidence"],
        "tags": decision["tags"],
        "reasoning": decision["reasoning"],
    }
