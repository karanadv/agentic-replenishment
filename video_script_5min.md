# 5-minute video script

This is the version to record. It runs three edge cases rather than four — the lead-time
disruption is deliberately dropped, for reasons noted at the end — and comes to roughly
857 spoken words. That's about 5:25 at an unhurried 155 words per minute, or just under
5:00 at a normal presenting pace of 175. If you tend to speak slowly, drop the closing
paragraph of Section 4 — the defect and defect-count beat — which brings it to 4:50 either way.

Every figure below was verified against the current engine. If a number on screen disagrees
with the script, the deployed app is running older code — push the current `engine/` files
and reboot before recording.

**Before you start:** open `diagrams/as_is_process_diagram_only.svg` and
`diagrams/agentic_workflow_diagram_only.svg` in browser tabs. Use the diagram-only versions,
not the full ones — those carry paragraphs of body text that are unreadable on a screen share.

---

## Section 1 — The two workflows (0:00–0:55)

**[Show `as_is_process_diagram_only.svg`]**

"Replenishment at this retailer is entirely manual. A planner exports sales from the ERP,
scrolls a spreadsheet, sets reorder quantities on judgement, and keys them back in — about
half a day, every week. There's no review step and no audit trail. Six months later nobody,
including the planner, can say why an order was four hundred units rather than two hundred."

**[Show `agentic_workflow_diagram_only.svg`]**

"I rebuilt it as an agentic loop — sense, decide, act, escalate. The agent reads the data,
sizes a reorder with an explicit confidence score, drafts the order with its reasoning
attached, and holds back anything it's unsure about or anything about to run dry. The
planner isn't removed from the loop. Their judgement is concentrated at the one point it's
worth spending, instead of being spread across every step with nothing checked."

## Section 2 — The prototype and three hard cases (0:55–2:55)

**[Switch to the running app, Dashboard tab]**

"Twenty-six weeks of synthetic data, fifteen products, split by online and in-store channel.
Every row is a recommendation the agent has already computed, sorted by confidence — the
buckle at 40% and the jacket at 50% sit at the top, and the products it has no doubts about
sit below."

**[Select APP-1042 in the SKU selector]**

"**The jacket that went viral.** It normally sells 39 a week. For three weeks it sold 188,
176, 188 — mostly online, from an influencer video.

The obvious fix is to fall back to a longer averaging window and let the spike wash out.
That doesn't work, and this is the most instructive thing in the build: the spike weeks sit
*inside* that longer window too. The eight-week average is 95 units against a true baseline
of 42. The first version of this system was over-ordering by more than double while its own
reasoning told the planner it had corrected for the spike.

So the agent now excludes the flagged event weeks outright and sizes against 42 — and the
reasoning says explicitly that the eight-week figure isn't a clean baseline either.
Confidence drops to 50%."

**[Select APP-2210]**

"**The customers who quietly moved online.** Total units barely move — around thirty a week,
before and after. Nothing looks unusual in the total at all.

Underneath, in-store sales collapsed from sixteen a week to three while online climbed from
fourteen to twenty-two. Customers migrated and the stock allocation didn't follow them. No
amount of looking at the combined figure would surface this. It's visible only because the
two channels are sensed separately — which is the whole argument for splitting them."

**[Select ACC-9981]**

"**The buckle nobody notices.** Sold in three of the last twelve weeks. A standard formula
still produces a number here, but the number is meaningless — an average of almost nothing
is still almost nothing.

So the agent says so. It flags insufficient history, drops confidence to 40%, and checks
what's already on the shelf: three units covers the 0.6 units of demand expected over the
lead time. It recommends ordering nothing at all, and flags it for a planner to confirm."

## Section 3 — Trust and control (2:55–3:55)

**[Switch to Needs review tab]**

"This is the trust layer. Anything below the confidence threshold, or anything urgent, lands
here with its full reasoning — approve as-is, edit the quantity, or reject with a stated
reason."

**[Click Approve edited or Reject on one item]**

"The queue is ordered by exposure — units of demand that go unserved, valued at retail. The
jacket sits at the top carrying three risk tags at once. The two footwear lines below it are
a supplier whose lead time doubled from port congestion, so they're short too."

**[Drag the sidebar confidence slider all the way down to 0.00]**

"And here's the part I'd point at first. The threshold is a live control — but drag it to
zero and the buckle *stays* in review. There's a hard floor at 50% the planner can't lower.

That item's own reasoning says it has too little history to trust a demand average. If the
agent has declared something beyond its own competence, an autonomy dial shouldn't be able
to wave it through. A trust layer you can instruct to trust itself completely isn't a trust
layer."

## Section 4 — Limitations and decisions (3:55–5:00)

**[Show `decisions_README.md`, scroll to Limitations]**

"Twenty-three limitations are recorded, in the same detail as the fixes. The thresholds are
hand-tuned against invented data. The spike measure itself saturates because the averaging
windows overlap, so a product whose demand merely doubles still reads as stable.

The scope boundary I'd name explicitly is BOPIS and BORIS — buy online and pick up in store,
and buy online and return in store. Neither was considered in the design. Pickup reserves
stock before collection, so shelf stock stops being sellable stock; returns push units back
at an unpredictable time and often a different store. They pull the arithmetic in opposite
directions — ignoring pickup makes the system under-order, ignoring returns makes it
over-order.

And one thing I'd call a defect rather than a decision: the urgent flag holds the purchase
order, but justifies itself in fulfilment terms. For a confident recommendation that delays
the very replenishment that ends the stockout. That's a routing rebuild, so it's documented
as a known defect rather than quietly left to look clean.

Seventeen defects were found and fixed across this build, two only visible because fixing
something else exposed them. The decisions README carries the reasoning behind every call —
including, for eight of them, what would make that call wrong."

---

## Why the lead-time case was dropped

The four hard cases in the build are the demand spike, the hidden channel shift, the
long-tail product, and a supplier lead time doubling from 21 to 45 days. The last one is cut
from this script.

It's the only case where the correct behaviour is what anyone would already expect —
supplier takes longer, so order earlier and bigger. There's no counterintuitive turn and no
moment where the naive answer is wrong. It's also the only one of the four with no defect
behind it: the other three each carry a mistake that was found and corrected, which is the
material that actually demonstrates engineering judgement.

The two footwear lines still appear in the review queue, so the script covers them in half a
line rather than leaving an unexplained product on screen.

If you'd rather record all four, `video_script_full_4cases.md` in this folder is the longer
version — around 8 minutes at unhurried pace, with cuttable passages marked.

## Recording checklist

- [ ] Both diagram-only SVGs open in browser tabs
- [ ] App running at https://agentic-replenishment-cfz5mznsmvyujuc692qt9e.streamlit.app/ with the slider at 0.70
- [ ] `decisions_README.md` open and scrolled to Limitations
- [ ] One item ready in the review queue to click Approve or Reject on
- [ ] Only one slider move needed: drag 0.70 straight down to 0.00, buckle stays put
- [ ] **Pre-flight the numbers.** Queue reads APP-1042, FTW-3301, FTW-3302, then ACC-9981. Three items marked urgent. Jacket recommends 83 units. If any differ, the deployed app is on older code
- [ ] Say the live URL out loud once so it's captured in the recording
