"""
DECIDE stage.

Turns sensed features into: a recommended reorder quantity, a
confidence score (0-1), a list of plain-language reasoning strings,
and a set of edge-case tags. Every number here traces back to a
readable rule — nothing is a black box, which is the point: a planner
should be able to check this logic by hand if they want to.
"""

SPIKE_RATIO_THRESHOLD = 1.4      # trailing_4wk / trailing_8wk above this = likely spike
# The symmetric counterpart. Because the 4wk window is nested inside the 8wk one,
# the ratio is algebraically 2X/(X+Y) and saturates at 2.0, so neither threshold
# means what it looks like: 1.4 implies recent demand is ~2.33x the prior 4 weeks,
# and 0.71 implies it has fallen to ~0.56x. Without this second check, a demand
# collapse falls through to the "looks stable" branch at 95% confidence and the
# system keeps ordering against an average the market has already left behind.
DECLINE_RATIO_THRESHOLD = 0.71
SPARSE_HISTORY_THRESHOLD = 0.35  # fewer than this fraction of last-12-weeks nonzero = long-tail
SAFETY_STOCK_WEEKS_FACTOR = 0.5  # safety stock = this * weekly demand basis
CHANNEL_RATIO_GAP_THRESHOLD = 0.6   # one channel trending up, the other down/flat, by this much
ALLOCATION_GAP_THRESHOLD = 0.20     # online demand share vs. online-allocated stock share, pct points
# Urgency scales with the SIZE of the projected stockout, not its mere existence.
# A bare "cover < lead time" test fires on roughly half the catalog — including
# SKUs that run dry a day early — which makes the flag noise rather than signal.
# This requires the shelf to be empty for a meaningful stretch before escalating.
STOCKOUT_GAP_URGENT_DAYS = 7


def decide(feature_row: dict) -> dict:
    reasoning = []
    tags = []
    confidence = 0.95  # start high, subtract as uncertainty signals appear
    urgent = False     # forces escalation regardless of confidence threshold

    trailing_4wk = feature_row["trailing_4wk_avg"]
    trailing_8wk = feature_row["trailing_8wk_avg"]
    spike_ratio = feature_row["spike_ratio"]
    nonzero_ratio = feature_row["nonzero_week_ratio"]
    lead_time = feature_row["current_lead_time_days"]
    lead_time_changed = feature_row["lead_time_changed"]
    on_hand = feature_row["on_hand_units"]
    # Reorder against inventory POSITION (on hand + already on order), not
    # on-hand alone. Ordering against on-hand double-counts demand that an
    # in-flight purchase order is already covering.
    inventory_position = feature_row["inventory_position"]
    has_open_po = feature_row["has_open_po"]

    # --- 1. Long-tail / sparse-history check (runs first: if data is too
    #     thin, nothing downstream can be trusted, so we short-circuit) ---
    if nonzero_ratio < SPARSE_HISTORY_THRESHOLD:
        tags.append("long_tail_sparse_history")
        confidence -= 0.55
        reasoning.append(
            f"Only sold in {feature_row['nonzero_week_count']} of the last 12 weeks — "
            "too little history to trust a demand average."
        )
        # Conservative means the LOWER of the two windows, not the higher:
        # on data this thin, a single lumpy week can drag the short window up,
        # and over-ordering a slow mover ties up cash in stock that won't move.
        demand_basis = min(trailing_8wk, trailing_4wk)
        lead_time_demand = demand_basis * (lead_time / 7.0)
        # net off stock already on hand and already on order — without this the
        # system reorders regardless of how much cover it already has
        recommended_qty = max(0, round(lead_time_demand - inventory_position))
        if recommended_qty == 0:
            reasoning.append(
                f"{inventory_position} units on hand or on order already covers the "
                f"~{lead_time_demand:.1f} units expected over the {lead_time}-day lead time — "
                "no reorder needed, but flagged so a planner can confirm."
            )
        else:
            reasoning.append(
                f"Minimal reorder of ~{recommended_qty} units ({inventory_position} on hand or on "
                f"order against ~{lead_time_demand:.1f} units of lead-time demand), flagged for "
                "manual sizing."
            )
    else:
        # --- 2. Demand spike check ---
        if spike_ratio >= SPIKE_RATIO_THRESHOLD:
            tags.append("demand_spike")
            confidence -= 0.25
            clean_baseline = feature_row["clean_baseline"]
            excluded = feature_row["excluded_week_count"]
            demand_basis = clean_baseline
            if excluded > 0:
                reasoning.append(
                    f"Recent 4-week average ({trailing_4wk}/wk) is {spike_ratio}x the "
                    f"8-week average ({trailing_8wk}/wk) — likely a temporary spike, not a new "
                    f"baseline. Sizing against {clean_baseline}/wk, the average of the last 12 weeks "
                    f"with the {excluded} flagged event week(s) excluded. Note the 8-week average "
                    f"({trailing_8wk}/wk) is itself inflated by those weeks, so it isn't a clean baseline."
                )
            else:
                reasoning.append(
                    f"Recent 4-week average ({trailing_4wk}/wk) is {spike_ratio}x the "
                    f"8-week average ({trailing_8wk}/wk) — an unexplained jump with no flagged "
                    f"promo or press event. Sizing against the 12-week average ({clean_baseline}/wk) "
                    "and flagging for review, since the cause is unknown."
                )
                confidence -= 0.1
        elif spike_ratio <= DECLINE_RATIO_THRESHOLD:
            tags.append("demand_decline")
            confidence -= 0.25
            # Size against the RECENT window, not the 8wk average. The 8wk figure
            # still carries the higher pre-decline weeks, so ordering against it
            # pushes stock into a SKU the market is already walking away from.
            demand_basis = trailing_4wk
            reasoning.append(
                f"Recent 4-week average ({trailing_4wk}/wk) has fallen to {spike_ratio}x the "
                f"8-week average ({trailing_8wk}/wk) — demand is declining, not stable. Sizing "
                f"against the recent {trailing_4wk}/wk rather than the 8-week average, which still "
                "includes the higher pre-decline weeks. Flagged because ordering into a decline ties "
                "up cash in stock that may not sell."
            )
        else:
            demand_basis = (trailing_4wk + trailing_8wk) / 2
            reasoning.append(
                f"Demand looks stable (4wk avg {trailing_4wk}/wk vs 8wk avg {trailing_8wk}/wk)."
            )

        safety_stock = demand_basis * SAFETY_STOCK_WEEKS_FACTOR
        reorder_point = demand_basis * (lead_time / 7.0) + safety_stock
        recommended_qty = max(0, round(reorder_point - inventory_position))
        if has_open_po:
            reasoning.append(
                f"{feature_row['on_order_units']} units are already on order, arriving in "
                f"{feature_row['on_order_arrival_days']} days. The reorder is sized against "
                f"{inventory_position} units of inventory position (on hand plus on order), not "
                f"the {on_hand} physically on the shelf — otherwise it would order again for "
                "demand a purchase order already covers."
            )

    # --- 3. Lead-time disruption check (applies regardless of the branch above) ---
    if lead_time_changed:
        tags.append("lead_time_disruption")
        confidence -= 0.2
        reasoning.append(
            f"Supplier lead time is currently {lead_time} days (was "
            f"{feature_row['standard_lead_time_days']} days) — {feature_row['disruption_note'] or 'a known disruption'}. "
            "Reorder quantity and timing both account for the longer wait."
        )

    # --- 4. Channel divergence check: catches a channel shift that's
    #     invisible in the aggregate (one channel up, the other down/flat) ---
    channel_ratio_gap = feature_row["channel_ratio_gap"]
    allocation_gap = feature_row["allocation_gap"]
    trend_diverged = channel_ratio_gap >= CHANNEL_RATIO_GAP_THRESHOLD
    allocation_mismatched = abs(allocation_gap) >= ALLOCATION_GAP_THRESHOLD

    # Each clause gets its own message. The two say different things and only
    # one may have fired — asserting an allocation problem when only the trend
    # clause tripped would be telling the planner something the rule never checked.
    if trend_diverged:
        tags.append("channel_divergence")
        confidence -= 0.2
        reasoning.append(
            f"Online and in-store demand are moving in opposite directions "
            f"(online trending {feature_row['online_ratio']}x vs. store {feature_row['store_ratio']}x "
            "against their own 8-week averages). The combined total can look flat while the mix "
            "underneath it shifts."
        )

    if allocation_mismatched:
        if "channel_divergence" not in tags:
            tags.append("channel_divergence")
            confidence -= 0.2
        if allocation_gap > 0:
            reasoning.append(
                f"Online is {feature_row['online_demand_share_now']:.0%} of recent demand but only "
                f"{feature_row['online_allocation_pct']:.0%} of stock is allocated to online fulfilment "
                "— demand has moved to online faster than inventory allocation has followed."
            )
        else:
            reasoning.append(
                f"Online is {feature_row['online_demand_share_now']:.0%} of recent demand but "
                f"{feature_row['online_allocation_pct']:.0%} of stock is allocated to online fulfilment "
                "— stock is over-committed to online while demand has moved back in-store."
            )

    # --- 5. Stockout-risk / customer-experience impact check. This doesn't
    #     simulate actual store-by-store fulfillment routing (this dataset
    #     has one shared on-hand pool, not per-store inventory), but flags
    #     the moment that would matter: if stock runs out before the next
    #     reorder arrives, in-store-pickup promises break and stores would
    #     need cross-location fulfillment workarounds to cover it. ---
    days_of_cover = feature_row["days_of_cover"]
    stockout_gap_days = feature_row["stockout_gap_days"]
    units_at_risk = feature_row["units_at_risk"]
    revenue_at_risk = feature_row["revenue_at_risk"]
    if stockout_gap_days >= STOCKOUT_GAP_URGENT_DAYS:
        tags.append("stockout_risk_cx_impact")
        urgent = True
        arrival_phrase = (
            f"the {feature_row['on_order_units']} units already on order do not land for "
            f"{feature_row['on_order_arrival_days']} days"
            if has_open_po else
            f"a reorder placed today takes {lead_time} days to arrive"
        )
        reasoning.append(
            f"On-hand stock covers ~{days_of_cover:.0f} days at the current sell-through rate, but "
            f"{arrival_phrase} — roughly {stockout_gap_days:.0f} days with nothing on the shelf, or "
            f"about {units_at_risk:.0f} units of demand left unserved ({revenue_at_risk:,.0f} at "
            "retail). During that window in-store pickup promises break and stores would need "
            "cross-location fulfillment to cover orders. Flagged regardless of forecast confidence, "
            "since this is an operational timing risk, not a demand-accuracy one."
        )

    confidence = max(0.05, min(0.99, round(confidence, 2)))

    return {
        "sku_id": feature_row["sku_id"],
        "sku_name": feature_row["sku_name"],
        "recommended_qty": int(recommended_qty),
        "confidence": confidence,
        "urgent": urgent,
        "revenue_at_risk": feature_row["revenue_at_risk"] if urgent else 0.0,
        "tags": tags,
        "reasoning": reasoning,
    }
