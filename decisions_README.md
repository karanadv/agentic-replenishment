# Decisions README

This documents the reasoning behind the key choices in this build — what I chose, why, and what I traded off.

## 1. Rule-based logic instead of an LLM

The brief listed the LLM requirement as "NA." Reorder recommendation is fundamentally a
statistics problem — rolling averages, anomaly detection, confidence scoring — and rules
you can point to line-by-line are a stronger fit for a "trust & control" system than a
model whose reasoning can't be fully audited. A planner can check every number in this
system by hand if they want to. The trade-off: it won't generalize to signals I didn't
explicitly code for (see Limitations).

## 2. Sense / decide / act / escalate as separate modules, not one function

Each stage is its own file (`engine/sense.py`, `decide.py`, `act.py`, `escalate.py`) with
a single responsibility. This was a deliberate choice over a single "agent does everything"
script: it means each stage can be tested, audited, and explained independently, which
mirrors the brief's ask for a workflow that's articulated stage-by-stage, not a black box.

## 3. Confidence threshold as a tunable UI control, not a hardcoded constant

Rather than deciding upfront "everything auto-applies" or "everything needs approval" (the
open question from the workflow design step), the threshold is a slider the planner
controls live. This reflects a real trade-off in replenishment: too conservative and the
system creates no time savings; too permissive and mistakes ship. Making it visible and
adjustable — rather than baked in — puts that judgment call where it belongs, with the
human, not with the build.

## 4. Long-tail SKUs fail conservative, not confident

The naive reorder-point formula produces a technically-computable but meaningless number
for SKUs with almost no sales history (e.g. ACC-9981, 2 nonzero weeks out of 12). Rather
than presenting that number with false confidence, the system explicitly detects sparse
history, drops confidence sharply, and routes to review with a flag explaining why — "not
enough data" is treated as a legitimate decision, not a gap to paper over.

## 5. Demand spikes are discounted, not deleted

When the trailing 4-week average is running hot relative to the trailing 8-week average,
the system doesn't ignore the recent data — it explicitly flags the deviation and falls
back to the longer window as the basis, while lowering confidence and surfacing the
reasoning. This avoids the two failure modes on either side: over-ordering into a spike
that reverts, or dismissing a real, sustained demand shift.

## 6. Synthetic data over anything real

All data is generated (see `data/data_dictionary.md` and the generator script) rather than
scraped or based on a real retailer, both because no real dataset was provided and to keep
every edge case deterministic and explainable in the demo.

## Limitations

- **Rule thresholds are hand-tuned, not learned.** The spike ratio (1.4x), sparse-history
  cutoff (35% of weeks), and confidence penalties are reasonable starting points I chose
  by testing against this dataset — not values validated against real retail behavior.
  They'd need calibration against real data before this could be trusted in production.
- **No real feedback loop yet.** The audit trail logs planner decisions, but nothing
  currently feeds those corrections back into the decide stage's thresholds. That's
  designed for in the workflow (see Step 1) but not implemented — it's mocked as a
  labeled placeholder in the UI, not a working mechanism.
- **Single-snapshot inventory, not live.** `on_hand_units` is a static "as of today" number.
  A production system would need real-time inventory sync, not a CSV snapshot.
- **No supplier reliability modeling beyond lead time.** The lead-time disruption case
  only tracks days-to-deliver; it doesn't model, e.g., partial shipments or fill-rate
  history, which a real system would need.
- **The Streamlit UI wasn't runtime-tested in the build environment** (no network access
  to install Streamlit in this sandbox) — the underlying engine logic was fully tested,
  but the UI layer should be verified locally before relying on it for a live demo.
- **This would not be shipped as-is.** It's a prototype meant to demonstrate the
  sense-decide-act-escalate pattern and a trust/control layer, not a production
  replenishment system — it has no auth, no persistence beyond the session, and no
  integration with a real ERP.
