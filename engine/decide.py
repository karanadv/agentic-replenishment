"""
DECIDE stage.

Turns sensed features into: a recommended reorder quantity, a
confidence score (0-1), a list of plain-language reasoning strings,
and a set of edge-case tags. Every number here traces back to a
readable rule — nothing is a black box, which is the point: a planner
should be able to check this logic by hand if they want to.
"""

SPIKE_RATIO_THRESHOLD = 1.4      # trailing_4wk / trailing_8wk above this = likely spike
SPARSE_HISTORY_THRESHOLD = 0.35  # fewer than this fraction of last-12-weeks nonzero = long-tail
SAFETY_STOCK_WEEKS_FACTOR = 0.5  # safety stock = this * weekly demand basis


def decide(feature_row: dict) -> dict:
    reasoning = []
    tags = []
    confidence = 0.95  # start high, subtract as uncertainty signals appear

    trailing_4wk = feature_row["trailing_4wk_avg"]
    trailing_8wk = feature_row["trailing_8wk_avg"]
    spike_ratio = feature_row["spike_ratio"]
    nonzero_ratio = feature_row["nonzero_week_ratio"]
    lead_time = feature_row["current_lead_time_days"]
    lead_time_changed = feature_row["lead_time_changed"]
    on_hand = feature_row["on_hand_units"]

    # --- 1. Long-tail / sparse-history check (runs first: if data is too
    #     thin, nothing downstream can be trusted, so we short-circuit) ---
    if nonzero_ratio < SPARSE_HISTORY_THRESHOLD:
        tags.append("long_tail_sparse_history")
        confidence -= 0.55
        reasoning.append(
            f"Only sold in {int(nonzero_ratio * 12)} of the last 12 weeks — "
            "too little history to trust a demand average."
        )
        # fall back to a minimal, conservative reorder rather than a
        # confident-looking number built on almost no data
        demand_basis = max(trailing_8wk, trailing_4wk, 0.5)
        recommended_qty = round(demand_basis * (lead_time / 7.0))
        reasoning.append(
            f"Falling back to a minimal reorder of ~{recommended_qty} units "
            "based on sparse historical average, flagged for manual sizing."
        )
    else:
        # --- 2. Demand spike check ---
        if spike_ratio >= SPIKE_RATIO_THRESHOLD:
            tags.append("demand_spike")
            confidence -= 0.25
            demand_basis = trailing_8wk  # discount the spike weeks
            reasoning.append(
                f"Recent 4-week average ({trailing_4wk}/wk) is {spike_ratio}x the "
                f"8-week average ({trailing_8wk}/wk) — likely a temporary spike, "
                "not a new baseline. Using the 8-week average instead of the inflated 4-week one."
            )
        else:
            demand_basis = (trailing_4wk + trailing_8wk) / 2
            reasoning.append(
                f"Demand looks stable (4wk avg {trailing_4wk}/wk vs 8wk avg {trailing_8wk}/wk)."
            )

        safety_stock = demand_basis * SAFETY_STOCK_WEEKS_FACTOR
        reorder_point = demand_basis * (lead_time / 7.0) + safety_stock
        recommended_qty = max(0, round(reorder_point - on_hand))

    # --- 3. Lead-time disruption check (applies regardless of the branch above) ---
    if lead_time_changed:
        tags.append("lead_time_disruption")
        confidence -= 0.2
        reasoning.append(
            f"Supplier lead time is currently {lead_time} days (was "
            f"{feature_row['standard_lead_time_days']} days) — {feature_row['disruption_note'] or 'a known disruption'}. "
            "Reorder quantity and timing both account for the longer wait."
        )

    confidence = max(0.05, min(0.99, round(confidence, 2)))

    return {
        "sku_id": feature_row["sku_id"],
        "sku_name": feature_row["sku_name"],
        "recommended_qty": int(recommended_qty),
        "confidence": confidence,
        "tags": tags,
        "reasoning": reasoning,
    }
