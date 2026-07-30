# 5-minute video script

A heads-up before you record: I don't have a tool that renders an actual video file in
this environment — no screen-recording or video-generation capability here. What follows
is a precise, timed script plus the two diagrams as standalone image files
(`diagrams/as_is_process.svg` and `diagrams/agentic_workflow.svg`) so you can record this
yourself in one take using Loom, QuickTime, or OBS. Open the two diagram SVGs in a browser
tab and the running app in another tab, and you're ready to go.

Total budget: 5:00. Section timings below add up to 5:00 — treat them as a guide, not a
stopwatch; natural pacing matters more than hitting the second mark exactly.

---

## Section 1 — As-is vs. agentic workflow, with diagrams (0:00–1:00)

**[Show diagrams/as_is_process.svg]**

"Today, replenishment for this retailer is entirely manual. A planner exports sales data
from the ERP, eyeballs trends with no systematic method, decides a reorder quantity on gut
feel, and keys it back in. There's no review step and no audit trail — one planner holds
all the judgment, and even they couldn't reconstruct why a decision was made a month later."

**[Show diagrams/agentic_workflow.svg]**

"I reimagined this as an agentic loop: the system senses demand and supply signals,
decides a recommendation with a confidence score, drafts it, and escalates anything it's
not sure about — or anything urgent — to a human. The planner isn't cut out of the loop;
their judgment is concentrated at the moments that actually need it — setting the
autonomy threshold, reviewing flagged items, approving, editing, or rejecting — instead of
being spread thin across every single step with nothing checked."

## Section 2 — Full prototype demo, all 4 edge cases (1:00–3:30)

**[Switch to the running app, Dashboard tab]**

"This is the working prototype — 26 weeks of synthetic sales, inventory, and supplier data
across 15 SKUs, split by online and in-store channel since this is an omnichannel
retailer. Every row here is a recommendation the agent already computed, sorted by
confidence so the least-certain ones float to the top."

**[Use the SKU selector to show each channel chart in turn]**

"**Demand spike — APP-1042**: this jacket saw a 4x jump in the last three weeks, mostly
online, from a viral moment. The obvious fix is to fall back to a longer averaging window —
but that doesn't work, because the spike weeks are inside that window too. The eight-week
average here is 95 units against a true baseline of 42. So the agent excludes the flagged
event weeks outright and sizes against 42, and it says so in the reasoning — including that
the eight-week figure isn't a clean baseline either. Confidence drops to 50%."

"**Hidden channel shift — APP-2210**: total units barely move week to week — nothing looks
unusual in the total. But online demand triples while store drops. This is only visible at
the channel level, and it matters because the stock allocated for online hasn't caught up."

"**Lead-time disruption — FTW-3301**: this footwear supplier's lead time jumped from 21 to
45 days from port congestion. The reorder math updates automatically, and it's flagged so
a planner knows why the number looks different."

"**Long-tail SKU — ACC-9981**: sold in only 2 of the last 12 weeks. Rather than confidently
computing a number off almost no data, the agent flags insufficient history and drops
confidence to 40%."

"One thing that isn't visible in these four but is worth mentioning: the same test runs in
the opposite direction. A SKU whose demand *collapses* gets flagged too, and gets sized
against its recent, lower demand — otherwise the system would order into a market it's
already losing while reporting itself confident."

**[Switch to Needs review tab]**

"This is the trust and control layer. Anything below the confidence threshold — or
anything urgent — lands here with its full reasoning. I can approve as-is, edit the
quantity, or reject with a reason."

**[Click Approve edited or Reject on one item]**

"Notice this one's marked urgent — that's a separate signal from confidence. It means
stock will run out before the next reorder arrives, which is exactly when in-store pickup
promises break and a store would need cross-location fulfillment. I didn't build that
routing — it's flagged so a human handles it instead of being silently auto-approved."

"The queue is ordered by exposure, not by confidence — units of demand that go unserved
during the gap, valued at retail. The jacket at the top has the *smallest* shortfall in days
of the three urgent items, but the highest exposure, because it sells far faster. Ranking by
days would have pushed it down the list."

"And one product that *was* urgent isn't here at all. It has a purchase order already in
flight, arriving inside its remaining cover — so the system knows the shortage is being dealt
with and stops raising it. Without that, the same items reappear every single run and people
stop reading the queue."

**[Drag the sidebar confidence slider from 0.70 to 0.80]**

"The threshold itself is a live control, not a hardcoded number. Watch — the channel-shift
SKU at 75% confidence just moved into the review queue. The spike SKU doesn't move, because
it's flagged urgent."

**[Drag the slider all the way down to 0.00]**

"And this is the part I'd point at first. The slider goes to zero, but the buckle SKU stays
in review — because there's a hard floor at 50% the planner can't lower. That item's own
reasoning says it has too little history to trust a demand average. If the agent has declared
something beyond its own competence, an autonomy dial shouldn't be able to wave it through.
A trust layer you can instruct to trust itself completely isn't a trust layer."

**[Switch to Audit trail tab]**

"Every decision gets logged here. In a full version, these corrections would feed back
into the agent's thresholds over time — that feedback loop is designed for, though not yet
wired up in this prototype."

## Section 3 — Data dictionary and README limitations (3:40–4:25)

**[Show data/data_dictionary.md]**

"All the data is synthetic, generated specifically for this project with four edge cases
deliberately baked in — the spike, the lead-time change, the long-tail SKU, and the hidden
channel shift. The data dictionary documents every column and exactly how each edge case
was constructed, so it's fully reproducible."

**[Show decisions_README.md, scroll to Limitations]**

"The decisions README is honest about what this prototype doesn't do. The rule thresholds
are hand-tuned against this dataset, not validated against real retail data. There's no
live feedback loop yet — it's designed for, not implemented. Inventory is one shared pool
per SKU, not per-store, so full fulfillment routing — buy-online-pickup-in-store,
ship-from-store, cross-location transfers — is out of scope; I surfaced the *signal* for
when those would be needed instead of simulating the routing itself. And the Streamlit UI
wasn't runtime-tested in the build sandbox, since it had no network access to install
Streamlit — I flagged that explicitly rather than claim more confidence than I had."

## Section 4 — Assumptions and key decisions (4:25–5:00)

"A few decisions worth calling out. First, no LLM — the brief listed it as not applicable,
and reorder recommendation is fundamentally a statistics problem, so I used fully
explainable rules instead of a black box. Second, the confidence threshold is a tunable
control, not a hardcoded constant, because how much autonomy the agent gets is a judgment
call that belongs to the planner — but it has a floor, because an unbounded version of that
control turned out to be incoherent. Third, long-tail SKUs and demand shifts both fail
*conservative*, not falsely confident — insufficient data becomes a legitimate, flagged
decision rather than a number dressed up to look certain. And fourth, urgency is ranked by
exposure rather than by shortfall in days, because ranking by days buried the highest-risk
item further down the list. And fifth, the system tracks orders already in flight — both so
alerts clear when a shortage is being handled, and so it doesn't re-order for demand an
existing purchase order already covers.

"One I'd call out as a defect rather than a decision: the urgent flag currently holds the
purchase order, but it justifies itself in fulfilment terms. For a high-confidence item
that means delaying the very replenishment that ends the stockout. The right design places
the order and escalates the customer-experience response separately. That's a routing
rebuild, so it's documented as a known defect rather than quietly left to look clean. The
decisions README carries the full reasoning, including what would make each of these calls
wrong."

---

## Recording checklist

- [ ] Open `diagrams/as_is_process.svg` and `diagrams/agentic_workflow.svg` in browser tabs
- [ ] App running locally or on the deployed URL (https://agentic-replenishment-cfz5mznsmvyujuc692qt9e.streamlit.app/), confidence slider reset to 0.70
- [ ] `data/data_dictionary.md` and `decisions_README.md` open and ready to scroll
- [ ] Have one item ready in the review queue to click Approve/Reject on
- [ ] Slider moves, in order: 0.70 → 0.80 (flips APP-2210 into review), then → 0.00 (ACC-9981 stays, held by the 50% floor)
- [ ] Say the live URL out loud once (https://agentic-replenishment-cfz5mznsmvyujuc692qt9e.streamlit.app/), so it's captured in the recording
