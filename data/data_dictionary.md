# Synthetic data — dictionary & edge cases

Three files, 26 weeks of history (`week_number` 1–26), 15 SKUs across 4 categories and 4 suppliers.

## sales_history.csv
One row per SKU per week.

| column | meaning |
|---|---|
| week_number | 1–26 |
| week_start_date | ISO date |
| sku_id / sku_name / category | product identity |
| units_sold | actual units sold that week |
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

| column | meaning |
|---|---|
| on_hand_units | current stock |
| current_lead_time_days | latest known lead time from suppliers.csv |
| trailing_4wk_avg_weekly_demand / trailing_8wk_avg_weekly_demand | rolling demand signals — comparing these two is one way to *detect* the spike edge case |
| safety_stock_units | naive buffer = 0.5 × trailing 8wk avg |
| reorder_point_units | naive reorder point = (trailing 8wk avg × lead_time/7) + safety stock |

`reorder_point_units` is intentionally computed with a naive formula. Part of the assignment is showing where the agent should *override or distrust* this naive number (e.g. the spike SKU's reorder point looks huge because it's built on an inflated trailing average; the long-tail SKUs' reorder points are near zero and not meaningful at all).

## Embedded edge cases

1. **Demand spike** — `APP-1042` (Trail Runner Jacket) sells 4x normal volume in weeks 20–22 (`promo_or_press_flag = 1`), then reverts. Trailing 4wk avg is inflated relative to the 8wk avg — a naive agent would over-order; a good agent should recognize the spike as transient and discount it.
2. **Supplier lead-time change** — `SUP-03` (Pacific Rim Footwear Ltd., supplies all `FTW-*` SKUs) has its lead time jump from 21 to 45 days starting week 19, with a `disruption_note`. Any FTW recommendation made after week 19 needs to account for the longer lead time or it will under-order.
3. **Long-tail SKU** — `ACC-9981` / `ACC-9982` (replacement buckles) sell 0–2 units in most weeks. A naive reorder formula produces near-zero, meaningless reorder points. The agent should flag these as low-confidence / insufficient-history rather than confidently recommending a tiny reorder quantity.
