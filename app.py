"""
Agentic Ops Build — replenishment prototype.

Streamlit is the whole UI layer here; all the actual "agent" logic
(sense -> decide -> act -> escalate) lives in engine/, imported below.
This file's job is just: render state, capture human decisions, log them.
"""

import streamlit as st
import pandas as pd
import altair as alt

from engine import sense, decide as decide_mod, act, escalate

st.set_page_config(page_title="Agentic Replenishment", layout="wide")

# ---------------------------------------------------------------------
# Load + compute (cached so the sidebar slider doesn't re-read CSVs)
# ---------------------------------------------------------------------
@st.cache_data
def load_and_compute():
    sales, suppliers, inventory = sense.load_data("data")
    features = sense.compute_features(sales, suppliers, inventory)
    drafts = []
    for _, row in features.iterrows():
        fr = row.to_dict()
        d = decide_mod.decide(fr)
        draft = act.draft_po(fr, d)
        drafts.append(draft)
    return sales, suppliers, features, drafts


sales, suppliers, features, drafts = load_and_compute()

if "decision_log" not in st.session_state:
    st.session_state.decision_log = []

# ---------------------------------------------------------------------
# Sidebar: the one tunable control from our workflow design
# ---------------------------------------------------------------------
st.sidebar.title("⚙️ Control layer")
threshold = st.sidebar.slider(
    "Confidence threshold for auto-approval",
    min_value=0.0, max_value=0.99, value=0.70, step=0.01,
    help="Recommendations below this confidence are held for planner review instead of auto-applied.",
)
st.sidebar.caption(
    "This is the knob from the workflow design step: how much the agent "
    "gets to act on its own vs. how much always comes back to a human."
)
st.sidebar.warning(
    f"**Hard floor: {escalate.AUTONOMY_FLOOR:.0%}.** Nothing below this auto-approves at "
    "any slider setting. When the agent has flagged a SKU as beyond its own competence, "
    "that isn't something an autonomy dial should be able to wave through."
)
st.sidebar.divider()
st.sidebar.metric("Total SKUs", len(drafts))
n_review = sum(1 for d in drafts if escalate.route(d, threshold) == "needs_review")
n_urgent = sum(1 for d in drafts if d["urgent"])
n_floor = sum(1 for d in drafts if d["confidence"] < escalate.AUTONOMY_FLOOR)
st.sidebar.metric("Flagged for review", n_review)
st.sidebar.metric("Urgent (stockout risk)", n_urgent)
st.sidebar.metric("Below autonomy floor", n_floor)

# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------
st.title("Agentic Replenishment — Planner Dashboard")
st.caption(
    "26 weeks of synthetic sales/inventory data. The agent senses demand + "
    "lead-time signals, decides a reorder quantity with a confidence score, "
    "drafts a PO, and escalates anything it isn't sure about."
)

tab_dashboard, tab_review, tab_audit = st.tabs(
    ["📊 Dashboard", "🔎 Needs review", "📜 Audit trail"]
)

# ---------------------------------------------------------------------
# Tab 1: Dashboard — everything at a glance
# ---------------------------------------------------------------------
with tab_dashboard:
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("All recommendations")
        rows = []
        for d in drafts:
            lane, why = escalate.route_with_reason(d, threshold)
            lane_label = {
                "below_autonomy_floor": "🔒 Below autonomy floor",
                "urgent_operational_risk": "🔴 Urgent (stockout risk)",
                "below_planner_threshold": "🟡 Needs review",
                "within_autonomy": "🟢 Auto-approved",
            }[why]
            rows.append({
                "SKU": d["sku_id"],
                "Name": d["sku_name"],
                "Qty": d["recommended_qty"],
                "On order": (f"{d['on_order_units']} in {d['on_order_arrival_days']}d"
                             if d["on_order_units"] else "—"),
                "Est. cost": f"${d['total_cost']:,.2f}",
                "Confidence": d["confidence"],
                "Lane": lane_label,
                "Tags": ", ".join(d["tags"]) if d["tags"] else "—",
            })
        df = pd.DataFrame(rows).sort_values("Confidence")
        st.dataframe(df, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Demand by channel: the 4 edge cases")
        pick = st.selectbox(
            "SKU",
            options=[
                "APP-1042 (demand spike)",
                "APP-2210 (hidden channel shift)",
                "FTW-3301 (lead-time disruption)",
                "ACC-9981 (long-tail)",
            ],
        )
        sku_id = pick.split()[0]
        chart_data = sales[sales.sku_id == sku_id][["week_number", "channel", "units_sold"]]
        chart = (
            alt.Chart(chart_data)
            .mark_bar()
            .encode(
                x="week_number:O",
                y="units_sold:Q",
                color=alt.Color("channel:N", scale=alt.Scale(domain=["online", "store"])),
            )
            .properties(height=260)
        )
        st.altair_chart(chart, use_container_width=True)
        if sku_id == "APP-2210":
            st.caption(
                "Total units per week barely move — but online (bottom of each bar) "
                "climbs while store drops. That shift is invisible if you only look at the total."
            )

# ---------------------------------------------------------------------
# Tab 2: Needs review — the actual trust & control layer
# ---------------------------------------------------------------------
with tab_review:
    st.subheader("Recommendations held for planner review")
    review_drafts = [d for d in drafts if escalate.route(d, threshold) == "needs_review"]
    # Ordered by exposure, not by SKU order or confidence: a queue that doesn't
    # rank is one a planner works top-to-bottom by accident. Items with no
    # stockout exposure sort below those with it, then by ascending confidence.
    review_drafts.sort(key=lambda d: (-d["revenue_at_risk"], d["confidence"]))

    if not review_drafts:
        st.info("Nothing is currently below the confidence threshold. Try lowering the slider.")

    for d in review_drafts:
        with st.container(border=True):
            _, why = escalate.route_with_reason(d, threshold)
            reason_label = {
                "below_autonomy_floor": "🔒 Below autonomy floor — cannot be auto-approved",
                "urgent_operational_risk": "🔴 URGENT — stockout risk",
                "below_planner_threshold": "🟡 Below your confidence threshold",
            }.get(why, "")
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{d['sku_id']} — {d['sku_name']}** {reason_label}")
                st.caption(f"Tags: {', '.join(d['tags'])}")
                for r in d["reasoning"]:
                    st.write(f"- {r}")
            with c2:
                st.metric("Confidence", f"{d['confidence']:.0%}")
                st.metric("Recommended qty", d["recommended_qty"])
                if d["revenue_at_risk"] > 0:
                    st.metric("Revenue at risk", f"{d['revenue_at_risk']:,.0f}")

            edited_qty = st.number_input(
                "Approve with quantity:", min_value=0, value=d["recommended_qty"], key=f"qty_{d['sku_id']}"
            )
            b1, b2, b3 = st.columns(3)
            if b1.button("✅ Approve", key=f"approve_{d['sku_id']}"):
                st.session_state.decision_log.append({
                    "sku_id": d["sku_id"], "action": "approved", "qty": edited_qty, "note": "",
                })
                st.success(f"Approved {d['sku_id']} at qty {edited_qty}")
            if b2.button("✏️ Approve edited", key=f"edit_{d['sku_id']}"):
                st.session_state.decision_log.append({
                    "sku_id": d["sku_id"], "action": "edited", "qty": edited_qty, "note": "Quantity adjusted by planner",
                })
                st.success(f"Logged edited quantity for {d['sku_id']}: {edited_qty}")
            reject_note = b3.text_input("Reason if rejecting", key=f"note_{d['sku_id']}", label_visibility="collapsed", placeholder="Reason if rejecting")
            if st.button("❌ Reject", key=f"reject_{d['sku_id']}"):
                st.session_state.decision_log.append({
                    "sku_id": d["sku_id"], "action": "rejected", "qty": 0, "note": reject_note or "No reason given",
                })
                st.warning(f"Rejected {d['sku_id']}")

# ---------------------------------------------------------------------
# Tab 3: Audit trail — the feedback-loop artifact from our workflow design
# ---------------------------------------------------------------------
with tab_audit:
    st.subheader("Planner decision log")
    st.caption(
        "Every approval, edit, or rejection is logged here. In a production version, "
        "rejections and edits would feed back into the decide stage's thresholds — "
        "the feedback loop from the workflow design."
    )
    if st.session_state.decision_log:
        st.dataframe(pd.DataFrame(st.session_state.decision_log), use_container_width=True, hide_index=True)
    else:
        st.info("No decisions logged yet — approve or reject something in the 'Needs review' tab.")
