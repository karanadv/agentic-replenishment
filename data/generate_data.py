"""
Synthesizes 26 weeks of sales + inventory + supplier data for the
Agentic Ops Build case, split across online and in-store channels
(this is an omnichannel retailer). Four edge cases are deliberately
embedded:

1. DEMAND SPIKE           -> SKU "APP-1042" (Trail Runner Jacket) spikes 4x
                             in the last 3 weeks (viral moment), driven mostly
                             through the online channel.
2. LEAD-TIME CHANGE       -> Supplier "SUP-03" (overseas footwear factory)
                             lead time jumps from 21 -> 45 days starting week 18
                             (port congestion), affects all their SKUs.
3. LONG-TAIL SKU          -> SKU "ACC-9981"/"ACC-9982" (Replacement Buckles)
                             have sparse, lumpy sales, sold almost entirely
                             in-store (register add-on item).
4. CHANNEL SHIFT (hidden  -> SKU "APP-2210" (Merino Base Layer): online demand
   in the aggregate)         triples and store demand drops correspondingly in
                             the last 4 weeks, so the TOTAL stays roughly flat.
                             An aggregate-only view sees nothing unusual; only
                             a channel-level view catches the shift.

Output: sales_history.csv, inventory_snapshot.csv, suppliers.csv
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta

rng = np.random.default_rng(42)

N_WEEKS = 26
START_DATE = date(2026, 1, 5)  # first Monday of the window
week_dates = [START_DATE + timedelta(weeks=i) for i in range(N_WEEKS)]

# ---------------------------------------------------------------------
# Catalog: SKUs across categories, each tagged with a supplier + a demand
# profile. Most SKUs are "normal" (steady with noise + mild trend).
# ---------------------------------------------------------------------
catalog = [
    # sku_id,     name,                          category,     supplier_id, base_weekly_demand, unit_cost, unit_price
    ("APP-1042", "Trail Runner Jacket",           "Apparel",    "SUP-01", 38,  42.00,  95.00),
    ("APP-2210", "Merino Base Layer",              "Apparel",    "SUP-01", 26,  18.50,  48.00),
    ("APP-2255", "Fleece Vest",                    "Apparel",    "SUP-02", 21,  22.00,  55.00),
    ("FTW-3301", "Trail Runner Shoe - Men's",      "Footwear",   "SUP-03", 45,  38.00,  110.00),
    ("FTW-3302", "Trail Runner Shoe - Women's",    "Footwear",   "SUP-03", 41,  38.00,  110.00),
    ("FTW-3350", "Hiking Sandal",                  "Footwear",   "SUP-03", 17,  24.00,  65.00),
    ("EQP-4410", "45L Backpack",                   "Equipment",  "SUP-02", 14,  55.00,  145.00),
    ("EQP-4455", "2-Person Tent",                  "Equipment",  "SUP-04", 9,   88.00,  220.00),
    ("EQP-4478", "Trekking Poles (Pair)",          "Equipment",  "SUP-02", 19,  19.00,  49.00),
    ("ACC-9901", "Wool Socks (3-pack)",            "Accessory",  "SUP-01", 55,  8.50,   22.00),
    ("ACC-9915", "Insulated Water Bottle",         "Accessory",  "SUP-04", 33,  6.00,   19.00),
    ("ACC-9930", "Headlamp",                       "Accessory",  "SUP-04", 24,  9.50,   28.00),
    ("ACC-9981", "Replacement Buckle, Blue",       "Accessory",  "SUP-02", 1.2, 1.20,   6.00),   # long-tail
    ("ACC-9982", "Replacement Buckle, Black",      "Accessory",  "SUP-02", 1.4, 1.20,   6.00),   # long-tail
    ("APP-2299", "Rain Shell",                     "Apparel",    "SUP-01", 16,  31.00,  85.00),
]

suppliers_master = {
    "SUP-01": {"name": "Highline Textiles Co.",       "standard_lead_time_days": 14},
    "SUP-02": {"name": "Ridgeline Gear Manufacturing", "standard_lead_time_days": 18},
    "SUP-03": {"name": "Pacific Rim Footwear Ltd.",    "standard_lead_time_days": 21},
    "SUP-04": {"name": "Summit Outdoor Supply",        "standard_lead_time_days": 25},
}

LEAD_TIME_CHANGE_WEEK = 18   # 0-indexed week when SUP-03 disruption starts
LEAD_TIME_CHANGE_SUPPLIER = "SUP-03"
LEAD_TIME_NEW_DAYS = 45
LEAD_TIME_CHANGE_NOTE = "Port congestion at origin port reported by supplier; lead time extended"

SPIKE_SKU = "APP-1042"
SPIKE_WEEKS = [23, 24, 25]     # 0-indexed -> weeks 24-26, i.e. still ongoing as of "today"
SPIKE_MULTIPLIER = 4.0
SPIKE_NOTE = "Featured in a viral trail-running influencer video (unplanned press mention)"
SPIKE_ONLINE_SHARE = 0.80      # the viral moment drove orders mostly online

CHANNEL_SHIFT_SKU = "APP-2210"
CHANNEL_SHIFT_WEEKS = [22, 23, 24, 25]   # 0-indexed -> weeks 23-26
CHANNEL_SHIFT_ONLINE_SHARE = 0.88        # online share jumps here; total volume is NOT boosted

LONG_TAIL_SKUS = {"ACC-9981", "ACC-9982"}

# Open purchase orders already in flight at the snapshot date. Without these,
# the system has no way to know a shortage is already being dealt with, so it
# re-raises the same alert every run and double-counts demand it has already
# ordered against. FTW-3350 was flagged short last cycle and a PO was placed;
# ACC-9901 is a routine high-volume replenishment mid-transit.
OPEN_POS = {
    "FTW-3350": {"units": 120, "arrival_days": 12},
    "ACC-9901": {"units": 200, "arrival_days": 5},
}

# Baseline online-vs-store demand split by category (an omnichannel retailer:
# every SKU sells through both, in different proportions)
CATEGORY_ONLINE_SHARE = {
    "Apparel": 0.45,
    "Footwear": 0.40,
    "Equipment": 0.30,
    "Accessory": 0.15,
}
LONG_TAIL_ONLINE_SHARE = 0.04   # register add-on item, almost never bought online

# Supply-side: fraction of on-hand stock allocated/reserved for online
# fulfillment (ship-from-DC / ship-from-store), vs. store shelf stock.
# Deliberately stale (doesn't track demand) for the two channel-shift SKUs,
# to model the real failure mode: allocation not keeping pace with where
# demand actually moved.
CATEGORY_ONLINE_ALLOCATION = dict(CATEGORY_ONLINE_SHARE)  # same defaults elsewhere
STALE_ALLOCATION_SKUS = {SPIKE_SKU: 0.25, CHANNEL_SHIFT_SKU: 0.40}

# ---------------------------------------------------------------------
# Generate weekly sales history, split by channel
# ---------------------------------------------------------------------
rows = []
for sku_id, name, category, supplier_id, base_demand, unit_cost, unit_price in catalog:
    # mild upward seasonal trend across the window (winter -> spring gear demand)
    trend = np.linspace(0.9, 1.15, N_WEEKS)
    baseline_online_share = LONG_TAIL_ONLINE_SHARE if sku_id in LONG_TAIL_SKUS else CATEGORY_ONLINE_SHARE[category]

    for w in range(N_WEEKS):
        if sku_id in LONG_TAIL_SKUS:
            # long-tail: mostly zero, occasional small order, high relative variance
            total_units = rng.poisson(base_demand) if rng.random() < 0.4 else 0
        else:
            noise = rng.normal(1.0, 0.12)
            total_units = max(0, round(base_demand * trend[w] * noise))

        promo_flag = 0

        # bake in the demand spike (total volume up, driven mostly online)
        if sku_id == SPIKE_SKU and w in SPIKE_WEEKS:
            total_units = round(total_units * SPIKE_MULTIPLIER)
            online_share_this_week = SPIKE_ONLINE_SHARE
            promo_flag = 1
        # bake in the channel shift (total volume roughly UNCHANGED, only the
        # online/store mix flips -- this is what's invisible in an aggregate view)
        elif sku_id == CHANNEL_SHIFT_SKU and w in CHANNEL_SHIFT_WEEKS:
            online_share_this_week = CHANNEL_SHIFT_ONLINE_SHARE
        else:
            online_share_this_week = min(0.95, max(0.02, baseline_online_share + rng.normal(0, 0.04)))

        online_units = int(round(total_units * online_share_this_week))
        store_units = int(total_units - online_units)

        for channel, units in [("online", online_units), ("store", store_units)]:
            rows.append({
                "week_number": w + 1,
                "week_start_date": week_dates[w].isoformat(),
                "sku_id": sku_id,
                "sku_name": name,
                "category": category,
                "channel": channel,
                "units_sold": int(units),
                "unit_price": unit_price,
                "promo_or_press_flag": promo_flag,
            })

sales_df = pd.DataFrame(rows)

# ---------------------------------------------------------------------
# Suppliers table: one row per supplier per week, capturing the lead-time
# change event explicitly so it's queryable as a time series
# ---------------------------------------------------------------------
sup_rows = []
for supplier_id, info in suppliers_master.items():
    for w in range(N_WEEKS):
        lead_time = info["standard_lead_time_days"]
        note = ""
        if supplier_id == LEAD_TIME_CHANGE_SUPPLIER and w >= LEAD_TIME_CHANGE_WEEK:
            lead_time = LEAD_TIME_NEW_DAYS
            note = LEAD_TIME_CHANGE_NOTE
        sup_rows.append({
            "week_number": w + 1,
            "supplier_id": supplier_id,
            "supplier_name": info["name"],
            "lead_time_days": lead_time,
            "disruption_note": note,
        })
suppliers_df = pd.DataFrame(sup_rows)

# ---------------------------------------------------------------------
# Inventory snapshot: current on-hand state "as of" the end of week 26,
# this is the state the agent sees "today" when it makes recommendations.
# on_hand_units is one shared DC pool; online_allocation_pct is the share
# of that pool earmarked for online fulfillment (supply-side, separate
# from the demand-side channel split above).
# ---------------------------------------------------------------------
inv_rows = []
for sku_id, name, category, supplier_id, base_demand, unit_cost, unit_price in catalog:
    sku_sales = sales_df[sales_df.sku_id == sku_id].groupby("week_number")["units_sold"].sum().sort_index()
    trailing_4wk_avg = sku_sales.tail(4).mean()
    trailing_8wk_avg = sku_sales.tail(8).mean()

    current_lead_time = suppliers_df[
        (suppliers_df.supplier_id == supplier_id) & (suppliers_df.week_number == N_WEEKS)
    ]["lead_time_days"].iloc[0]

    # on-hand roughly sized to look plausible against demand, with some
    # SKUs deliberately left thin (so recommendations trigger for them)
    if sku_id == SPIKE_SKU:
        on_hand = 22       # thin, because the spike blew through stock
    elif sku_id in LONG_TAIL_SKUS:
        on_hand = int(rng.integers(3, 9))
    elif supplier_id == LEAD_TIME_CHANGE_SUPPLIER:
        on_hand = int(round(trailing_4wk_avg * 2.5))
    else:
        on_hand = int(round(trailing_4wk_avg * rng.uniform(2.0, 4.0)))

    safety_stock = round(trailing_8wk_avg * 0.5, 1)
    reorder_point = round(trailing_8wk_avg * (current_lead_time / 7.0) + safety_stock, 1)

    online_allocation_pct = STALE_ALLOCATION_SKUS.get(
        sku_id,
        LONG_TAIL_ONLINE_SHARE if sku_id in LONG_TAIL_SKUS else CATEGORY_ONLINE_ALLOCATION[category],
    )

    inv_rows.append({
        "sku_id": sku_id,
        "sku_name": name,
        "category": category,
        "supplier_id": supplier_id,
        "on_hand_units": on_hand,
        "on_order_units": OPEN_POS.get(sku_id, {}).get("units", 0),
        "on_order_arrival_days": OPEN_POS.get(sku_id, {}).get("arrival_days", 0),
        "online_allocation_pct": round(online_allocation_pct, 2),
        "unit_cost": unit_cost,
        "unit_price": unit_price,
        "current_lead_time_days": current_lead_time,
        "trailing_4wk_avg_weekly_demand": round(trailing_4wk_avg, 2),
        "trailing_8wk_avg_weekly_demand": round(trailing_8wk_avg, 2),
        "safety_stock_units": safety_stock,
        "reorder_point_units": reorder_point,
    })

inventory_df = pd.DataFrame(inv_rows)

# ---------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------
sales_df.to_csv("sales_history.csv", index=False)
suppliers_df.to_csv("suppliers.csv", index=False)
inventory_df.to_csv("inventory_snapshot.csv", index=False)

print("sales_history.csv:", sales_df.shape)
print("suppliers.csv:", suppliers_df.shape)
print("inventory_snapshot.csv:", inventory_df.shape)
print()
print("Spike check (APP-1042, weeks 23-26, by channel):")
print(sales_df[(sales_df.sku_id == "APP-1042") & (sales_df.week_number.between(23, 26))][["week_number", "channel", "units_sold"]])
print()
print("Channel-shift check (APP-2210, weeks 21-26, by channel):")
shift_check = sales_df[(sales_df.sku_id == "APP-2210") & (sales_df.week_number.between(21, 26))]
print(shift_check.pivot(index="week_number", columns="channel", values="units_sold"))
print("(totals per week, to show they stay roughly flat):")
print(shift_check.groupby("week_number")["units_sold"].sum())
print()
print("Lead-time change check (SUP-03, weeks 16-20):")
print(suppliers_df[(suppliers_df.supplier_id == "SUP-03") & (suppliers_df.week_number.between(16, 20))])
print()
print("Long-tail channel check (ACC-9981, totals by channel):")
print(sales_df[sales_df.sku_id == "ACC-9981"].groupby("channel")["units_sold"].sum())

