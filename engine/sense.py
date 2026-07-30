"""
SENSE stage.

Responsible only for perceiving the world: loading the raw data and
turning it into a clean feature set per SKU. No recommending, no
judging — that happens in decide.py. Keeping this boundary explicit
is deliberate: it's what makes the pipeline auditable stage-by-stage
rather than one opaque function.

This is an omnichannel retailer, so sales are split by channel
(online / store). Alongside the aggregate features, this stage also
computes channel-level signals — because a channel shift can be
completely invisible in an aggregate total (online up, store down,
total unchanged) while still being operationally important (wrong
inventory in the wrong place).
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


def _trailing_avgs(weekly_series: pd.Series) -> dict:
    return {
        "4wk": weekly_series.tail(4).mean(),
        "8wk": weekly_series.tail(8).mean(),
        "12wk": weekly_series.tail(12).mean(),
    }


def compute_features(sales: pd.DataFrame, suppliers: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per SKU with everything decide.py needs:
    aggregate trailing averages + spike ratio, sparse-history signal,
    supplier lead-time-change signal, AND per-channel trailing averages
    + a channel-divergence signal.
    """
    features = []

    for _, inv_row in inventory.iterrows():
        sku_id = inv_row["sku_id"]
        supplier_id = inv_row["supplier_id"]
        sku_sales = sales[sales.sku_id == sku_id]

        # --- aggregate (both channels combined) ---
        weekly_total = sku_sales.groupby("week_number")["units_sold"].sum().sort_index()
        agg = _trailing_avgs(weekly_total)
        trailing_4wk, trailing_8wk, trailing_12wk = agg["4wk"], agg["8wk"], agg["12wk"]
        spike_ratio = (trailing_4wk / trailing_8wk) if trailing_8wk > 0 else 1.0

        nonzero_weeks = (weekly_total.tail(12) > 0).sum()
        nonzero_ratio = nonzero_weeks / 12.0

        # --- clean baseline: trailing demand EXCLUDING weeks with a known
        # external demand event (promo / press). Falling back to a longer
        # trailing window as the "spike-corrected" basis doesn't actually
        # work, because the spike weeks sit inside that window too and still
        # inflate it. Excluding the flagged weeks outright gives the real
        # underlying demand level, which is what a reorder should be sized on.
        weekly_flag = sku_sales.groupby("week_number")["promo_or_press_flag"].max().sort_index()
        recent_weeks = weekly_total.tail(12)
        recent_flags = weekly_flag.reindex(recent_weeks.index).fillna(0)
        clean_weeks = recent_weeks[recent_flags == 0]
        excluded_week_count = int((recent_flags == 1).sum())
        # if every recent week was flagged there's no clean signal to fall back
        # on, so keep the 12wk average and let confidence carry the doubt
        clean_baseline = clean_weeks.mean() if len(clean_weeks) > 0 else trailing_12wk

        # --- per-channel ---
        weekly_online = sku_sales[sku_sales.channel == "online"].groupby("week_number")["units_sold"].sum().sort_index()
        weekly_store = sku_sales[sku_sales.channel == "store"].groupby("week_number")["units_sold"].sum().sort_index()
        online_avg = _trailing_avgs(weekly_online)
        store_avg = _trailing_avgs(weekly_store)

        online_ratio = (online_avg["4wk"] / online_avg["8wk"]) if online_avg["8wk"] > 0 else 1.0
        store_ratio = (store_avg["4wk"] / store_avg["8wk"]) if store_avg["8wk"] > 0 else 1.0

        # current demand mix: what share of recent (4wk) demand is online
        recent_total = online_avg["4wk"] + store_avg["4wk"]
        online_demand_share_now = (online_avg["4wk"] / recent_total) if recent_total > 0 else 0.0

        # channel divergence: one channel trending up while the other trends
        # down/flat, even if the aggregate ratio looks unremarkable
        channel_ratio_gap = abs(online_ratio - store_ratio)

        # --- lead time ---
        current_lead_time = suppliers[
            (suppliers.supplier_id == supplier_id) & (suppliers.week_number == LATEST_WEEK)
        ]["lead_time_days"].iloc[0]
        standard_lead_time = STANDARD_LEAD_TIMES[supplier_id]
        lead_time_changed = current_lead_time > standard_lead_time
        disruption_note = suppliers[
            (suppliers.supplier_id == supplier_id) & (suppliers.week_number == LATEST_WEEK)
        ]["disruption_note"].iloc[0]

        # --- supply-side channel allocation vs. where demand actually is ---
        online_allocation_pct = inv_row["online_allocation_pct"]
        allocation_gap = online_demand_share_now - online_allocation_pct  # positive = demand outpacing allocation

        # --- days of cover: how long on-hand stock lasts at the current
        # sell-through rate, vs. how long a reorder takes to arrive. This is
        # the signal for CX-impacting stockout risk (BOPIS promises breaking,
        # needing cross-store/warehouse fulfillment) without simulating
        # actual store-by-store routing, which this dataset doesn't model.
        # Uses the CURRENT burn rate (trailing 4wk), not the spike-discounted
        # 8wk figure. Discounting a spike when sizing an order is defensible;
        # discounting it when assessing stockout risk is not — stock depletes
        # at the rate it's actually selling, and using the smoothed number
        # would understate the risk exactly when it's highest.
        current_burn_rate = max(trailing_4wk, trailing_8wk) / 7.0
        days_of_cover = (inv_row["on_hand_units"] / current_burn_rate) if current_burn_rate > 0 else 999.0

        # --- open purchase orders already in flight. Two things depend on this.
        # First, the shortage horizon: if stock is already on its way, the gap
        # runs to THAT arrival, not to the lead time of a hypothetical new
        # order. Without it the system re-raises an identical alert every run
        # for a shortage a planner already acted on, which is how alert
        # fatigue starts. Second, inventory position (below): reordering
        # against on-hand alone double-counts demand already ordered against.
        on_order = inv_row.get("on_order_units", 0)
        on_order_arrival_days = inv_row.get("on_order_arrival_days", 0)
        has_open_po = on_order > 0
        next_arrival_days = on_order_arrival_days if has_open_po else current_lead_time
        inventory_position = inv_row["on_hand_units"] + on_order

        # --- exposure: how much demand actually goes unserved during the gap.
        # This is deliberately built from information the reorder calculation
        # never touches (unit price), because otherwise "urgency" is just a
        # severity band on the same axis as "needs reorder" rather than a
        # second dimension. Two SKUs with the same shortfall in days can carry
        # very different exposure depending on how fast they sell and what
        # they are worth.
        stockout_gap_days = max(0.0, next_arrival_days - days_of_cover)
        units_at_risk = stockout_gap_days * current_burn_rate
        revenue_at_risk = units_at_risk * inv_row["unit_price"]

        features.append({
            "sku_id": sku_id,
            "sku_name": inv_row["sku_name"],
            "category": inv_row["category"],
            "supplier_id": supplier_id,
            "on_hand_units": inv_row["on_hand_units"],
            "on_order_units": on_order,
            "on_order_arrival_days": on_order_arrival_days,
            "has_open_po": has_open_po,
            "inventory_position": inventory_position,
            "next_arrival_days": next_arrival_days,
            "unit_cost": inv_row["unit_cost"],
            "unit_price": inv_row["unit_price"],
            "trailing_4wk_avg": round(trailing_4wk, 2),
            "trailing_8wk_avg": round(trailing_8wk, 2),
            "trailing_12wk_avg": round(trailing_12wk, 2),
            "spike_ratio": round(spike_ratio, 2),
            "clean_baseline": round(clean_baseline, 2),
            "excluded_week_count": excluded_week_count,
            "nonzero_week_ratio": round(nonzero_ratio, 2),
            "nonzero_week_count": int(nonzero_weeks),
            "current_lead_time_days": current_lead_time,
            "standard_lead_time_days": standard_lead_time,
            "lead_time_changed": lead_time_changed,
            "disruption_note": disruption_note if isinstance(disruption_note, str) else "",
            "days_of_cover": round(days_of_cover, 1),
            "stockout_gap_days": round(stockout_gap_days, 1),
            "units_at_risk": round(units_at_risk, 1),
            "revenue_at_risk": round(revenue_at_risk, 2),
            # channel-level
            "online_4wk_avg": round(online_avg["4wk"], 2),
            "store_4wk_avg": round(store_avg["4wk"], 2),
            "online_ratio": round(online_ratio, 2),
            "store_ratio": round(store_ratio, 2),
            "channel_ratio_gap": round(channel_ratio_gap, 2),
            "online_demand_share_now": round(online_demand_share_now, 2),
            "online_allocation_pct": round(online_allocation_pct, 2),
            "allocation_gap": round(allocation_gap, 2),
        })

    return pd.DataFrame(features)
