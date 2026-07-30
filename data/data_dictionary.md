# Synthetic data — dictionary & edge cases

**Live app:** https://agentic-replenishment-cfz5mznsmvyujuc692qt9e.streamlit.app/

Three files, 26 weeks of history (`week_number` 1–26), 15 SKUs across 4 categories and 4 suppliers.
This is an **omnichannel retailer** — every SKU sells through both an online and an
in-store channel, split at different rates by category.

## sales_history.csv
One row per SKU per week **per channel** (`online` or `store`).

| column | meaning |
|---|---|
| week_number | 1–26 |
| week_start_date | ISO date |
| sku_id / sku_name / category | product identity |
| channel | `online` or `store` |
| units_sold | actual units sold through that channel that week |
| unit_price | retail price |
| promo_or_press_flag | 1 if an external demand event (e.g. press mention) is known to have driven that week's sales |

## suppliers.csv
One row per supplier per week (so lead-time changes are a time series, not a static fact).

| column | meaning |
|---|---|
| week_number | 1–26 |
| supplier_id / supplier_name | supplier identity |
| lead_time_days | lead time in effect that week |
| disruption_note | free text, populated only during a disruption window |

## inventory_snapshot.csv
One row per SKU — the state as of the end of week 26 ("today," when the agent runs).
This models **one shared on-hand pool per SKU** (not per-store inventory), with a
supply-side split of how much of that pool is earmarked for online fulfillment.

| column | meaning |
|---|---|
| on_hand_units | current stock physically available (shared pool, not broken out by physical store) |
| on_order_units | units already on an open purchase order, not yet arrived (0 if none in flight) |
| on_order_arrival_days | days until that open order lands (0 if none in flight) |
| online_allocation_pct | share of on-hand stock earmarked/reserved for online fulfillment (a supply-side allocation — separate from where demand is actually coming from) |
| current_lead_time_days | latest known lead time from suppliers.csv |
| trailing_4wk_avg_weekly_demand / trailing_8wk_avg_weekly_demand | rolling demand signals — comparing these two is one way to *detect* the spike edge case |
| safety_stock_units | naive buffer = 0.5 × trailing 8wk avg |
| reorder_point_units | naive reorder point = (trailing 8wk avg × lead_time/7) + safety stock |

`reorder_point_units` is intentionally computed with a naive formula. Part of the assignment is showing where the agent should *override or distrust* this naive number (e.g. the spike SKU's reorder point looks huge because it's built on an inflated trailing average; the long-tail SKUs' reorder points are near zero and not meaningful at all).

## Embedded edge cases

1. **Demand spike** — `APP-1042` (Trail Runner Jacket) sells 4x normal volume in the last 3 weeks (`promo_or_press_flag = 1`), driven mostly through the online channel. Trailing 4wk avg is inflated relative to the 8wk avg — a naive agent would over-order; a good agent should recognize the spike as transient and discount it.
2. **Supplier lead-time change** — `SUP-03` (Pacific Rim Footwear Ltd., supplies all `FTW-*` SKUs) has its lead time jump from 21 to 45 days starting week 19, with a `disruption_note`. Any FTW recommendation made after week 19 needs to account for the longer lead time or it will under-order.
3. **Long-tail SKU** — `ACC-9981` / `ACC-9982` (replacement buckles) sell 0–2 units in most weeks, almost entirely in-store (register add-on purchase, near-zero online). A naive reorder formula produces near-zero, meaningless reorder points. The agent should flag these as low-confidence / insufficient-history rather than confidently recommending a tiny reorder quantity.
4. **Hidden channel shift** — `APP-2210` (Merino Base Layer): in the last 4 weeks, online demand roughly triples while store demand drops correspondingly, so the **total stays roughly flat**. An aggregate-only view sees nothing unusual (`spike_ratio` stays near 1.0). Only a channel-level view — comparing online-only and store-only trailing averages — catches that demand has moved, which matters because `online_allocation_pct` (stock reserved for online) hasn't been updated to match.

## Omnichannel signals (channel-level, computed in `engine/sense.py`)

- **channel_ratio_gap** — how far apart the online-only and store-only spike ratios are; large gap = one channel trending up while the other trends down/flat, even if the total looks stable.
- **online_demand_share_now vs. online_allocation_pct** — compares where demand actually is (recent online share of sales) against where stock is allocated. A large gap means inventory hasn't caught up to a channel shift.
- **inventory position** — on-hand plus on-order. Reorder quantities are netted against this rather than against on-hand alone; ordering against on-hand double-counts demand an in-flight purchase order already covers. On this dataset that prevents a 79-unit double-order on `FTW-3350`.
- **days_of_cover** — on-hand stock ÷ the *current* daily sell-through rate. This deliberately uses the higher of the trailing 4-week and 8-week rates rather than the spike-discounted figure: discounting a spike when sizing an order is defensible, but stock depletes at the rate it is actually selling, so using the smoothed number would understate risk exactly when it is highest. The gap is measured to the **next actual arrival** — an open purchase order if one is in flight, otherwise the lead time of an order placed today. Without that, the system re-raises an identical alert every run for a shortage a planner has already acted on. When the projected gap reaches **7 days or more** — meaning roughly a week with nothing on the shelf — the SKU is flagged **urgent** regardless of forecast confidence, since it's a timing risk, not a demand-accuracy one. A bare "cover < lead time" test was tried first and fired on more than half the catalog, including SKUs running dry a single day early, which made the flag noise rather than signal.

Note: full **fulfillment orchestration** (in-store pickup routing, ship-from-store, buy-online-return-in-store, cross-store/warehouse transfers) is out of scope for this prototype — it requires per-store inventory and an order-routing layer, which is a different system from replenishment planning. The `days_of_cover` / urgent flag is a deliberately lightweight signal that surfaces *when* those workarounds would be needed, without simulating the routing itself. See the decisions README for the full reasoning.

