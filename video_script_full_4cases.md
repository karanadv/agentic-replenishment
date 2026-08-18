# 5-minute video script

A heads-up before you record: I don't have a tool that renders an actual video file in
this environment — no screen-recording or video-generation capability here. What follows
is a precise, timed script plus the two diagrams as standalone image files. Each diagram
comes in two forms: the full version with written explanation below it, and a
`_diagram_only` version cropped to the process itself. **Use the diagram-only versions on
camera** — the full ones carry paragraphs nobody can read on a screen share:
`diagrams/as_is_process_diagram_only.svg` and `diagrams/agentic_workflow_diagram_only.svg`.
Open both in browser tabs and the running app in another, and you're ready to record in one
take using Loom, QuickTime, or OBS.

Every number quoted below was verified against the current engine. If a figure on screen
disagrees with the script, the deployed app is running older code — push the current
`engine/` files and reboot before recording.

**This script currently runs long.** At a natural 155 words per minute the full text is
roughly eight minutes of speech, not five — it has accumulated material across several
rounds of changes. Two options:

- **Record the full version (~8 min)** if the brief tolerates overrunning. Nothing in it is
  padding, and the extra minutes are spent on the trust layer and the limitations, which are
  the parts that carry the most weight.
- **Cut using the marked passages below.** Everything tagged **[CUT FOR 5:00]** can be
  dropped without breaking the narrative. That removes about 330 words and brings the script
  to roughly 960 spoken words — about 6:10 at an unhurried 155 wpm, or a little under 5:30 if
  you speak at 175. Getting genuinely under 5:00 would mean cutting one of the four edge
  cases, which costs more than it saves.

Be honest with yourself about pace when deciding. If you tend to speak quickly the cut
version lands close enough to five minutes; if you don't, either accept a six-minute
recording or drop the lead-time case, which is the least surprising of the four.

Section timings assume the cut version. Treat them as a guide, not a stopwatch.

---

## Section 1 — As-is vs. agentic workflow, with diagrams (0:00–1:00)

**[Show diagrams/as_is_process_diagram_only.svg]**

"Today, replenishment for this retailer is entirely manual. A planner exports sales data
from the ERP, eyeballs trends with no systematic method, decides a reorder quantity on gut
feel, and keys it back in. There's no review step and no audit trail — one planner holds
all the judgment, and even they couldn't reconstruct why a decision was made a month later."

**[Show diagrams/agentic_workflow_diagram_only.svg]**

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
confidence — so the buckle at 40% and the jacket at 50% sit at the top, and the steady
products the agent has no doubts about sit below."

**[Use the SKU selector to show each channel chart in turn]**

"**Demand spike — APP-1042**: this jacket saw a 4x jump in the last three weeks, mostly
online, from a viral moment. The obvious fix is to fall back to a longer averaging window —
but that doesn't work, because the spike weeks are inside that window too. The eight-week
average here is 95 units against a true baseline of 42. So the agent excludes the flagged
event weeks outright and sizes against 42, and it says so in the reasoning — including that
the eight-week figure isn't a clean baseline either. Confidence drops to 50%."

**[CUT FOR 5:00 — or compress to one sentence]**  "**Hidden channel shift — APP-2210**: total units barely move week to week — nothing looks
unusual in the total. But online demand triples while store drops. This is only visible at
the channel level, and it matters because the stock allocated for online hasn't caught up."

"**Lead-time disruption — FTW-3301**: this footwear supplier's lead time jumped from 21 to
45 days from port congestion. The reorder math updates automatically, and it's flagged so
a planner knows why the number looks different."

"**Long-tail SKU — ACC-9981**: sold in only 3 of the last 12 weeks. Rather than confidently
computing a number off almost no data, the agent flags insufficient history and drops
confidence to 40%. It also checks what's already on the shelf — three units covers the
0.6 units of demand expected over the lead time, so it recommends ordering nothing at all
and flags it for a planner to confirm."

**[CUT FOR 5:00]**  "One thing that isn't visible in these four but is worth mentioning: the same test runs in
the opposite direction. A SKU whose demand *collapses* gets flagged too, and gets sized
against its recent, lower demand — otherwise the system would order into a market it's
already losing while reporting itself confident."

**[Switch to Needs review tab]**

"This is the trust and control layer. Anything below the confidence threshold — or
anything urgent — lands here with its full reasoning. I can approve as-is, edit the
quantity, or reject with a reason."

**[Click Approve edited or Reject on one item]**

"Notice this one's marked urgent — that's a separate signal from confidence. It means
stock runs out a meaningful stretch before the next delivery lands, which is exactly when
in-store pickup promises break and a store would need cross-location fulfillment. I didn't
build that routing — it's flagged so a human handles it instead of being silently
auto-approved. The jacket at the top is carrying three risk tags at once: a demand spike,
a channel divergence, and this stockout gap."

**[CUT FOR 5:00 — the slider beat below makes the trust point better]**  "The queue is ordered by exposure, not by confidence — units of demand that go unserved
during the gap, valued at retail. The jacket at the top has the *smallest* shortfall in days
of the three urgent items, but the highest exposure, because it sells far faster. Ranking by
days would have pushed it down the list."

**[CUT FOR 5:00]**  "And one product that *was* urgent isn't here at all. It has a purchase order already in
flight, arriving inside its remaining cover — so the system knows the shortage is being dealt
with and stops raising it. Without that, the same items reappear every single run and people
stop reading the queue."

**[Drag the sidebar confidence slider from 0.70 to 0.80]**

**[CUT FOR 5:00 — go straight to the floor demo, which is the stronger moment]**  "The threshold itself is a live control, not a hardcoded number. Watch — the channel-shift
SKU at 75% confidence just moved into the review queue. The spike SKU doesn't move, because
it's flagged urgent."

**[Drag the slider all the way down to 0.00]**

"And this is the part I'd point at first. The slider goes to zero, but the buckle SKU stays
in review — because there's a hard floor at 50% the planner can't lower. That item's own
reasoning says it has too little history to trust a demand average. If the agent has declared
something beyond its own competence, an autonomy dial shouldn't be able to wave it through.
A trust layer you can instruct to trust itself completely isn't a trust layer."

**[CUT FOR 5:00 — skip this tab entirely]**

**[Switch to Audit trail tab]**

"Every decision gets logged here. In a full version, these corrections would feed back
into the agent's thresholds over time — that feedback loop is designed for, though not yet
wired up in this prototype."

## Section 3 — Data dictionary and README limitations (3:40–4:30)

**[Show data/data_dictionary.md]**

"All the data is synthetic, generated specifically for this project with four edge cases
deliberately baked in — the spike, the lead-time change, the long-tail SKU, and the hidden
channel shift. The data dictionary documents every column and exactly how each edge case
was constructed, so it's fully reproducible."

**[Show decisions_README.md, scroll to Limitations]**

"The decisions README is honest about what this prototype doesn't do. Twenty-three limitations
are recorded, with the same detail as the fixes. The thresholds are hand-tuned against this
dataset, not validated against real retail data — at realistic retail variability the
false-positive rate rises to around three percent. The spike measure itself is compressed by
overlapping windows and saturates at two, so a product whose demand merely doubles reads as
stable. And there's no live feedback loop: corrections are logged but change nothing."

**[KEEP — this is the strongest limitation beat]**  "The scope boundary I'd name explicitly is BOPIS and BORIS — buy online and pick up in store,
and buy online and return in store. Neither was considered in the design. Pickup reserves
stock against a named store before collection, so shelf stock stops being sellable stock;
returns push units back at an unpredictable time and often a different store. They pull the
arithmetic in opposite directions — ignoring pickup makes the system under-order, ignoring
returns makes it over-order. Neither is representable while inventory is one pooled figure."

## Section 4 — Assumptions and key decisions (4:30–5:00)

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

**[CUT FOR 5:00 if needed, but keep if at all possible]**  "One I'd call out as a defect rather than a decision: the urgent flag currently holds the
purchase order, but it justifies itself in fulfilment terms. For a high-confidence item
that means delaying the very replenishment that ends the stockout. The right design places
the order and escalates the customer-experience response separately. That's a routing
rebuild, so it's documented as a known defect rather than quietly left to look clean. The
decisions README carries the full reasoning, including what would make each of these calls
wrong."

---

## Recording checklist

- [ ] Open the **diagram-only** SVGs in browser tabs — `as_is_process_diagram_only.svg` and `agentic_workflow_diagram_only.svg` (not the full versions, which carry unreadable body text)
- [ ] App running locally or on the deployed URL (https://agentic-replenishment-cfz5mznsmvyujuc692qt9e.streamlit.app/), confidence slider reset to 0.70
- [ ] `data/data_dictionary.md` and `decisions_README.md` open and ready to scroll
- [ ] Have one item ready in the review queue to click Approve/Reject on
- [ ] Pre-flight the numbers: queue reads APP-1042, FTW-3301, FTW-3302, then ACC-9981; three items marked urgent; jacket recommends 83 units. If any of these differ, the deployed app is on older code
- [ ] Slider moves, in order: 0.70 → 0.80 (flips APP-2210 into review), then → 0.00 (ACC-9981 stays, held by the 50% floor)
- [ ] Say the live URL out loud once (https://agentic-replenishment-cfz5mznsmvyujuc692qt9e.streamlit.app/), so it's captured in the recording
