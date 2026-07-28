# Decisions README

**Live app:** https://agentic-replenishment-cfz5mznsmvyujuc692qt9e.streamlit.app/

This documents the reasoning behind the key choices in this build — what I chose, why, and what I traded off.

## 1. Rule-based logic instead of an LLM

The brief listed the LLM requirement as "NA." Reorder recommendation is fundamentally a
statistics problem — rolling averages, anomaly detection, confidence scoring — and rules a
planner can follow line by line fit a trust-and-control system better than a model whose
reasoning can't be reconstructed.

One distinction matters here, and the first draft of this document blurred it. Rules are
auditable in **mechanism**: a planner can trace exactly how a number was produced. They are
not thereby justified in **parameters**: the thresholds throughout this build are hand-tuned
constants with no derivation, so a planner can read the rule that fired and still have no
basis for judging whether 1.4 was the right cutoff. Transparency about how a decision was
computed is not the same as evidence that it was computed correctly, and this build only
delivers the first. See the Signal design limitations for what that costs.

*This would be the wrong call if* the useful signals turned out to be ones no one thought to
encode — unstructured supplier emails, competitor pricing, weather — which is exactly where
a learned model earns its opacity.

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
human, not with the build. Decision 10 later adds a floor beneath it, because an
unbounded version of this control turned out to be incoherent.

*This would be the wrong call if* planners in practice set the dial once and never revisit
it, in which case a visible control is just a hardcoded constant with extra steps.

## 4. Long-tail SKUs fail conservative, not confident

The naive reorder-point formula produces a technically-computable but meaningless number
for SKUs with almost no sales history (e.g. ACC-9981, 3 nonzero weeks out of 12). Rather
than presenting that number with false confidence, the system explicitly detects sparse
history, drops confidence sharply, and routes to review with a flag explaining why — "not
enough data" is treated as a legitimate decision, not a gap to paper over.

*This would be the wrong call if* the long tail were large enough that routing all of it to
manual review recreated the bottleneck the system exists to remove.

## 5. Demand spikes are excluded from the baseline, not smoothed over

When the trailing 4-week average runs hot against the trailing 8-week average, the system
flags the deviation, lowers confidence, and sizes the order against a **clean baseline** —
the last 12 weeks with the flagged event weeks removed entirely.

The obvious approach, and the one I built first, was to fall back to the longer 8-week
window as the "spike-corrected" basis. Testing showed that doesn't work: the spike weeks
sit *inside* that window too. For the demo SKU, the true pre-spike baseline is 42 units/week,
the inflated 4-week average is 149, and the supposedly-corrected 8-week average is 94.6 —
still more than double reality. The system would have over-ordered by ~2.25x while telling
the planner it had corrected for the spike. Excluding the flagged weeks outright gives 42,
and the reasoning string now says so explicitly, including a note that the 8-week figure
isn't a clean baseline either.

If a spike is detected with *no* flagged event explaining it, the system takes an extra
confidence penalty rather than assuming the cause is benign.

## 5b. Demand declines are checked, not just spikes

The spike test originally only asked whether recent demand had run *above* the longer
average. A collapse fell through to the "demand looks stable" branch and received 95%
confidence, while the system kept sizing orders against an 8-week average that still carried
the higher pre-decline weeks — ordering into a market it was already losing. A symmetric
decline check now sizes against the recent window instead and applies the same confidence
penalty as a spike. On a test SKU whose demand halved, this reduces the recommendation from
41 units to 26.

The threshold pair (1.4 up, 0.71 down) is deliberately not symmetric-looking, because the
underlying ratio is compressed by the nested windows: 1.4 corresponds to a ~2.33x rise and
0.71 to a fall to ~0.56x. That compression is documented under Limitations rather than
engineered around, since fixing it properly means moving to non-overlapping windows and
re-deriving every threshold.

## 5c. Urgency scales with the size of a stockout, not its existence

The first version of the stockout flag asked simply whether days of cover was less than
lead time. That fired on 8 of 15 SKUs — including ones that run dry a single day early —
which makes an "urgent" flag noise rather than signal. It now requires a projected gap of
at least 7 days with nothing on the shelf, which flags 4 of 15. Related: days of cover is
computed off the *current* burn rate, not the spike-discounted one. Discounting a spike
when sizing an order is defensible; discounting it when assessing how fast stock is actually
depleting is not.

## 6. Synthetic data over anything real

All data is generated (see `data/data_dictionary.md` and the generator script) rather than
scraped or based on a real retailer, both because no real dataset was provided and to keep
every edge case deterministic and explainable in the demo.

The cost is stated throughout Limitations and is worth collecting here: every threshold in
this build was tuned against data whose noise characteristics I chose. The generator
produces a coefficient of variation around 12%; real retail weekly demand commonly runs
35–60%. Detectors that look clean here have not been tested against the conditions they
would actually face.

## 7. Channel modelled on the demand side; inventory deployment left out, partly on principle and partly on budget

Sales are split by channel (online vs. in-store), but inventory remains **one shared on-hand
pool per SKU** with no named physical locations.

Part of that boundary is principled. Order *routing* — deciding which node serves a given
order at checkout — is an order-management concern operating on a different time horizon
from replenishment, and excluding it is defensible.

Part of it is not, and it is worth being precise about which. Inventory **deployment** —
how much stock goes to which DC or store — is core replenishment work, not order management,
and it genuinely requires per-location inventory. By excluding per-store inventory alongside
order routing, this build leaves out something that legitimately belongs inside an
omnichannel replenishment prototype. The honest account is that the boundary was drawn where
the time budget ran out, and it happens to coincide with a real architectural seam rather
than being derived from one.

What *is* modelled is where demand is coming from, plus `online_allocation_pct` — the share
of the shared pool earmarked for online fulfilment. That figure is **exogenous**: it is a
constant in the CSV that nothing decides, updates, or reacts to. It is enough to demonstrate
that an allocation-versus-demand mismatch is detectable; it is not evidence that the
detection generalises, since the only mismatches present are ones deliberately planted.

*This would be the wrong call if* the retailer's main replenishment pain were deployment
across locations rather than order sizing — in which case a single pooled inventory figure
models away the actual problem.

## 8. A channel shift invisible in the aggregate — what this does and does not show

One edge case (`APP-2210`) is built so online demand roughly triples while store demand falls
correspondingly, leaving the **total** volume roughly flat. An aggregate-only agent sees
nothing. The engine catches it only because it computes trailing averages *per channel*.

Two honest qualifications.

**This demonstrates a principle, not a validated detector.** The edge case was constructed so
that per-channel averages would diverge by a comfortably detectable margin, and the detector
was written knowing that. What it establishes is that aggregate-only sensing is structurally
blind to mix shifts — a real and non-obvious point. What it does not establish is that this
particular detector would catch a subtler or more gradual shift, or that it would stay quiet
on organic channel noise. Channel-level sensing also roughly doubles the signal surface and
therefore the false-positive exposure, a cost this build does not measure.

**Detection currently feeds a decision it has no bearing on.** Running `APP-2210` with the
divergence flagged versus suppressed produces an *identical* recommended quantity — the
signal moves confidence only. But the remedy for "demand moved online while stock is
allocated to store" is reallocation, not a different reorder quantity, and this system has no
reallocation action to take. So a correctly-detected signal is routed into the reorder
decision, where it can lower confidence but cannot produce the response it actually implies.
Closing that gap needs the per-location inventory model excluded in decision 7.

*This would be the wrong call if* channel mix in the real business were stable enough that
the extra false positives cost more than the missed shifts.

## 9. Stockout risk as an "urgent" flag — with a routing tension left unresolved

Customer-experience capabilities — pickup-in-store, ship-from-store, cross-location
fulfilment — were not built, for the scope reasons in decision 7. Instead a single signal
(`days_of_cover` against lead time, with the 7-day gap qualifier from decision 5c) marks SKUs
where stock runs out materially before resupply. It is escalated independently of the
confidence score, because it is an operational timing risk rather than a forecast-accuracy
question.

**The tension, stated up front rather than buried in Limitations:** this flag justifies
itself in fulfilment terms — pickup promises breaking, transfers being needed — but
`escalate.route()` gates the *purchase order*. For a high-confidence urgent item, holding the
PO for review delays the very replenishment that ends the stockout. The flag is attached to
the wrong artifact. The coherent design places the PO automatically and escalates the CX
response separately; that is a routing rebuild rather than a tweak, and it was not attempted
this late. It is a known defect, not a resolved design.

Two further overreaches worth naming. The signal flags a *state*, not a *moment* — there is
no "you breach in six days," and because it never clears (decision 5c, Limitations) it
re-flags the same state on every run. And the link from low days-of-cover to an actual
broken pickup promise is **asserted, not modelled**: there is no order data, no promise data
and no service-level target in this dataset to verify it against.

*This would be the wrong call if* purchasing latency mattered more than fulfilment
visibility — under which the current blocking behaviour is straightforwardly harmful.

## 10. The autonomy slider has a floor the planner cannot lower

The confidence threshold is a live control (decision 3), but it is not unbounded. Below a
hard floor of 50%, nothing auto-approves at any slider setting.

This closes an asymmetry the first version had. The urgent flag was un-overridable on the
argument that the agent shouldn't be able to wave past risks it had itself identified — but
the agent's own declaration that it lacks the data to judge a SKU was fully overridable.
`ACC-9981`'s reasoning reads "sold in only 3 of the last 12 weeks — too little history to
trust a demand average," and at a slider setting of 0.40 that item auto-approved with no
human ever seeing it. At 0.00, eleven of fifteen SKUs auto-approved including that one.

If the principle is that flagged incompetence shouldn't be slider-overridable, epistemic
uncertainty is the stronger case rather than the weaker one: a projected stockout is
something the agent computed correctly, whereas sparse history means it genuinely does not
know. A trust layer that can be instructed to trust itself completely isn't a trust layer.

The floor is set at 0.50 rather than higher because the confidence model in `decide.py`
leaves a SKU at 0.70–0.75 after a single uncertainty signal. A 0.50 floor therefore catches
the sparse-history case and anything stacking two or more independent signals, without
capturing routine flags and making the slider decorative.

`escalate.route_with_reason()` also returns *which* rule fired, so the dashboard and review
queue can tell a planner whether an item is in front of them because of the floor, an
operational risk, or their own threshold — rather than presenting one undifferentiated
"needs review" lane.

## 11. Urgency ranked by exposure, not by shortfall in days

The urgency flag originally asked only whether stock would run out before resupply, then
(decision 5c) whether the shortfall exceeded seven days. Both are severity bands on the same
axis. Working the arithmetic for a steady SKU, urgency fires below `D × LT/7 − D` while a
reorder triggers below `D × LT/7 + 0.5D` — so urgency was a strict subset of "needs reorder,"
offset by about 1.5 weeks of demand. Tightening the threshold improved discrimination without
adding a second dimension.

The queue is now ordered by **exposure**: units of demand left unserved during the gap,
valued at retail. That is deliberately built from information the reorder calculation never
uses — unit price — because otherwise it would be the same signal rescaled.

It changes the order materially. `APP-1042` has a 13-day shortfall against the footwear SKUs'
27-day shortfall, so the days-based measure ranks it fourth. But its burn rate is far higher,
giving it the largest exposure of any SKU in the catalogue, and the exposure measure ranks it
first. That is the ordering a planner would act on.

*Stated plainly:* on this dataset the exposure measure does **not** change which SKUs are
flagged — the same four surface either way. What it changes is the priority order within
them. It therefore does more to address the unranked-queue problem than the collinearity
problem. On data where a fast-moving SKU had a short shortfall and a slow mover a long one,
the flagged set would diverge too.

*This would be the wrong call if* stockouts on low-value items carried reputational cost out
of proportion to their revenue — in which case ranking by money actively buries them.

## Limitations

### Signal design

- **`spike_ratio` is structurally compressed by nested windows.** `trailing_4wk` is a subset
  of `trailing_8wk`, so the ratio is algebraically `2X/(X+Y)` and **saturates at 2.0** — a
  3.67x jump reports as 1.57, and a hypothetical 100x jump would report 1.98. The practical
  consequence is that the 1.4 threshold implicitly demands that recent demand be ~2.33x the
  preceding four weeks. A SKU whose demand sustainably **doubles** produces a ratio of 1.33
  and is classified "stable" at 95% confidence. Comparing non-overlapping windows (last 4
  weeks vs. the 4 before) would remove the compression, but it shifts every downstream
  threshold, so it is documented here rather than changed late.
- **The spike/decline thresholds are safe against this dataset's noise, and only this
  dataset's.** Simulating flat SKUs, the false-positive rate at 1.4 is 0.00% at the ~12%
  coefficient of variation this generator produces, 0.12% at CV 35%, and ~3% at CV 60%.
  Real retail weekly demand commonly sits in the 35–60% range, so the thresholds would need
  re-derivation — ideally as a z-score or robust (median/MAD) deviation against each SKU's
  own variability, rather than a single global constant applied to every SKU.
- **`channel_ratio_gap` is blind to direction.** It computes `|online_ratio - store_ratio|`,
  which flags "online 2.0 / store 1.3" — both channels growing — identically to a genuine
  opposite-direction split, while the reasoning string asserts the channels are "moving in
  opposite directions." A directional test should gate that message. Differencing ratios is
  also asymmetric: a doubling (2.0 vs 1.0) scores 1.00 while a halving (1.0 vs 0.5) scores
  0.50, though both are the same relative divergence. Log-space differencing gives 0.69 for
  both and is the standard treatment for ratio data.
- **`allocation_gap` has never been tested against organic drift.** It fires on exactly the
  two SKUs where the generator plants a deliberately stale allocation value, and on no
  others. That demonstrates the mechanism but is close to circular as evidence that the
  detector discriminates. It also has no volume gate: `online_demand_share_now` is estimated
  from the 4-week window, which for the long-tail SKUs is 1–4 observed units — a proportion
  estimated from four units cannot meaningfully be compared against a 20-point threshold.
- **`days_of_cover` carries no uncertainty.** It is a deterministic point estimate
  (`on_hand / daily_rate`), so "cover is less than lead time" is roughly a coin-flip
  statement rather than a service level. Genuine safety-stock planning models demand variance
  and targets an explicit stockout probability. It also ignores in-transit and on-order
  stock, which is harmless here only because this dataset models none.
- **The 4/8/12-week windows are conventional, not derived.** They map to roughly monthly,
  bimonthly and quarterly retail practice, but nothing in this build justifies them from the
  data — no autocorrelation analysis, no seasonal decomposition. Their nesting is what
  produces the compression described above, so the choice is not cosmetic. More
  fundamentally, 26 weeks of history cannot support seasonality estimation at all (that needs
  two-plus years), so any real seasonal pattern would be misread here as trend or as a spike.

### Routing and escalation

- **The urgent flag blocks the order that would relieve the urgency.** `decide.py` justifies
  the stockout flag in terms of fulfilment — pickup promises breaking, stores needing
  cross-location transfers — but `escalate.route()` gates the *purchase order*. For a
  high-confidence urgent item the agent is sure about the quantity and the problem is
  timing, so withholding the PO pending review delays the very replenishment that ends the
  stockout. The coherent design separates the two: auto-place the PO, and escalate the CX
  response (expedite, transfer, or suppress the pickup promise) as a distinct decision.
  Splitting them is a routing rebuild rather than a tweak, so it is named here rather than
  attempted late.
- **Escalation still collapses reasons into one lane, though it now ranks within it.**
  `route_with_reason()` reports which rule fired and the queue is ordered by exposure
  (decision 11), but there is still a single queue rather than separate workflows for
  "I am unsure about this number" and "this SKU is about to go dark." Those call for
  different responses from a planner and arguably belong in different places.
- **Urgency remains a severity band on the reorder axis, not an independent dimension.**
  Exposure-based ranking adds price information the reorder path does not use, which changes
  the ordering, but the *trigger* is still days-of-cover against lead time — arithmetically a
  subset of the reorder condition. A genuinely orthogonal urgency signal would need inputs
  this dataset does not contain: substitutability, promise sensitivity by channel, or an
  explicit service-level target per SKU.
- **Urgency never clears.** `days_of_cover` is computed from on-hand stock alone; nothing
  models on-order or in-transit inventory. A SKU therefore stays urgent on every run until
  physical stock arrives, regardless of whether a planner approved a PO for it yesterday.
  The same items reappear in the queue indefinitely with no acknowledged state, which is the
  standard path to alert fatigue. Fixing it requires modelling open purchase orders, which
  this dataset does not contain.

### Other limitations

- **Rule thresholds are hand-tuned, not learned.** The spike ratio (1.4x), decline ratio
  (0.71), sparse-history cutoff (35% of weeks), channel-divergence gap (0.6), allocation-gap
  threshold (20 points), stockout-gap urgency window (7 days), and confidence penalties are
  starting points chosen by testing against this dataset — not values validated against real
  retail behavior.
- **The sparse-history check measures frequency, not volume.** It asks how many of the last
  12 weeks had *any* sales, which misses a SKU that sells reliably but in tiny quantities.
  `ACC-9982` sells roughly one unit a week in 5 of 12 weeks, clears the 35% threshold, and
  therefore receives 95% confidence and a "demand looks stable" message — technically true,
  but a one-unit-a-week average carries almost no forecasting signal regardless of how
  regularly it appears. A volume floor alongside the frequency test would close this; I've
  left it out rather than add an untested rule late, but it's a real gap.
- **Confidence penalties are additive and clamped.** Each signal subtracts a fixed amount
  and the result is floored at 0.05. Independent uncertainties don't compose linearly, and
  once a SKU hits the floor, further signals convey no additional information. A
  multiplicative model would be more principled.
- **Safety stock is a flat half-week of demand**, unconnected to demand variability or lead
  time. Standard practice ties it to both. This is the assumption a working planner would
  challenge first.
- **The urgency flag is correlated with, not independent of, the reorder decision.** The
  stockout-gap test is arithmetically related to the lead-time demand component of the
  reorder point, so it identifies a severe subset of items needing reorder rather than a
  genuinely orthogonal risk dimension.
- **No minimum order quantities or case packs.** Recommendations come out as raw unit
  counts; real purchase orders are constrained to supplier case sizes and MOQs.
- **No real feedback loop yet.** The audit trail logs planner decisions, but nothing
  currently feeds those corrections back into the decide stage's thresholds. That's
  designed for in the workflow (see Step 1) but not implemented — it's mocked as a
  labeled placeholder in the UI, not a working mechanism.
- **Single-snapshot inventory, not live.** `on_hand_units` is a static "as of today" number.
  A production system would need real-time inventory sync, not a CSV snapshot.
- **No per-store inventory or fulfillment orchestration.** Inventory is one shared pool per
  SKU, not broken out by physical store. Customer-experience features like buy-online-pickup-
  in-store, ship-from-store, buy-online-return-in-store, and cross-store/warehouse fulfillment
  on stockout are real and valuable, but they belong to an order-management/fulfillment-
  routing system, not a replenishment-planning one — modeling them properly would require
  named store locations and a routing engine well beyond this prototype's scope. What this
  build does instead is surface the *signal* that would trigger those workarounds
  (`days_of_cover` / the urgent stockout-risk flag) without simulating the routing itself.
- **No supplier reliability modeling beyond lead time.** The lead-time disruption case
  only tracks days-to-deliver; it doesn't model, e.g., partial shipments or fill-rate
  history, which a real system would need.
- **The Streamlit UI was not runtime-tested during the build** (the build sandbox had no
  network access to install Streamlit), so the UI layer was verified only by deploying it
  afterwards, not by automated testing. The engine logic in `engine/` is verified
  end-to-end against all four edge cases.
- **This would not be shipped as-is.** It's a prototype meant to demonstrate the
  sense-decide-act-escalate pattern and a trust/control layer, not a production
  replenishment system — it has no auth, no persistence beyond the session, and no
  integration with a real ERP.
