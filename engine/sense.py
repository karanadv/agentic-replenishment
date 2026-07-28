"""
SENSE stage.

Responsible only for perceiving the world: loading the raw data and
turning it into a clean feature set per SKU. No recommending, no
judging — that happens in decide.py. Keeping this boundary explicit
is deliberate: it's what makes the pipeline auditable stage-by-stage
rather than one opaque function.
"""

import pandas as pd
from pathlib import Path

LATEST_WEEK = 26
STANDARD_LEAD_TIMES = {
    "SUP-01": 14,
    "SUP-02": 18,
    "SUP-03": 21,
    "SUP-04": 25,
}


def load_data(data_dir: str = "data"):
    data_dir = Path(data_dir)
    sales = pd.read_csv(data_dir / "sales_history.csv")
    suppliers = pd.read_csv(data_dir / "suppliers.csv")
    inventory = pd.read_csv(data_dir / "inventory_snapshot.csv")
    return sales, suppliers, inventory


def compute_features(sales: pd.DataFrame, suppliers: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per SKU with everything decide.py needs:
    trailing averages, a spike ratio, sparse-history signal, and
    whether the SKU's supplier just changed lead time.
    """
    features = []

    for _, inv_row in inventory.iterrows():
        sku_id = inv_row["sku_id"]
        supplier_id = inv_row["supplier_id"]
        sku_sales = sales[sales.sku_id == sku_id].sort_values("week_number")

        trailing_4wk = sku_sales.tail(4)["units_sold"].mean()
        trailing_8wk = sku_sales.tail(8)["units_sold"].mean()
        trailing_12wk = sku_sales.tail(12)["units_sold"].mean()

        # spike signal: how far the short window has run above the longer one
        spike_ratio = (trailing_4wk / trailing_8wk) if trailing_8wk > 0 else 1.0

        # sparse-history signal: fraction of the last 12 weeks with any sales at all
        nonzero_weeks = (sku_sales.tail(12)["units_sold"] > 0).sum()
        nonzero_ratio = nonzero_weeks / 12.0

        # lead-time-change signal: compare current lead time to the supplier's
        # standard (pre-disruption) lead time
        current_lead_time = suppliers[
            (suppliers.supplier_id == supplier_id) & (suppliers.week_number == LATEST_WEEK)
        ]["lead_time_days"].iloc[0]
        standard_lead_time = STANDARD_LEAD_TIMES[supplier_id]
        lead_time_changed = current_lead_time > standard_lead_time
        disruption_note = suppliers[
            (suppliers.supplier_id == supplier_id) & (suppliers.week_number == LATEST_WEEK)
        ]["disruption_note"].iloc[0]

        features.append({
            "sku_id": sku_id,
            "sku_name": inv_row["sku_name"],
            "category": inv_row["category"],
            "supplier_id": supplier_id,
            "on_hand_units": inv_row["on_hand_units"],
            "unit_cost": inv_row["unit_cost"],
            "trailing_4wk_avg": round(trailing_4wk, 2),
            "trailing_8wk_avg": round(trailing_8wk, 2),
            "trailing_12wk_avg": round(trailing_12wk, 2),
            "spike_ratio": round(spike_ratio, 2),
            "nonzero_week_ratio": round(nonzero_ratio, 2),
            "current_lead_time_days": current_lead_time,
            "standard_lead_time_days": standard_lead_time,
            "lead_time_changed": lead_time_changed,
            "disruption_note": disruption_note if isinstance(disruption_note, str) else "",
        })

    return pd.DataFrame(features)
