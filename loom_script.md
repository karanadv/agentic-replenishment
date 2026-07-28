# Loom walkthrough script (~4 minutes)

Tip: have the app open with the confidence slider at 0.70 before you hit record.

---

## 1. Frame the problem (30 sec)

"Today, replenishment for this retailer is manual — a planner exports sales data,
eyeballs trends, and keys in reorder quantities based on gut feel. That doesn't scale
past a handful of SKUs, and there's no record of *why* any decision was made.

I built a prototype that reimagines this as an agentic loop: the system senses demand
and supply signals, decides a recommendation with a confidence score, drafts it, and
escalates anything it's not sure about — while a human stays in control of anything
uncertain."

*(Optional: show the workflow diagram here for 5-10 seconds if you export it as an image.)*

## 2. Show the dashboard (45 sec)

Switch to the **Dashboard** tab.

"This is 26 weeks of synthetic sales, inventory, and supplier data across 15 SKUs, split
across online and in-store channels since this is an omnichannel retailer. Every row here
is a recommendation the agent already computed — quantity, confidence, and whether it's
auto-approved, needs review, or flagged urgent."

Point at the sorted-by-confidence table.

"Notice it's sorted by confidence — the ones the system is least sure about float to
the top automatically."

## 3. Walk through the four edge cases (100 sec)

Use the SKU selector to show each channel-split chart while narrating:

**Demand spike — APP-1042:**
"This jacket saw a 4x demand jump in the last three weeks — a viral video, driven mostly
through the online channel. A naive system might read that as the new normal and massively
over-order. Instead, the agent flags it as a likely spike, discounts it back to the 8-week
baseline, and drops its own confidence to 50% instead of pretending it's sure."

**Hidden channel shift — APP-2210:**
"This one's subtle: total units sold barely change week to week — nothing looks unusual in
the aggregate. But online demand triples while in-store drops. You can only see it here,
at the channel level. That matters because the stock allocated for online fulfillment hasn't
caught up to where demand actually moved."

**Lead-time disruption — FTW-3301:**
"This footwear supplier's lead time jumped from 21 to 45 days due to port congestion. The
reorder math updates automatically to account for the longer wait — and it's flagged so
a planner knows *why* the quantity looks different than usual."

**Long-tail SKU — ACC-9981:**
"This one only sold in 2 of the last 12 weeks. Rather than confidently computing a
number off almost no data, the agent recognizes it doesn't have enough history, drops
confidence to 40%, and routes it for manual sizing instead of guessing."

## 4. Show the trust & control layer (60 sec)

Switch to **Needs review** tab.

"This is the part I think matters most: the agent never just acts silently. Anything
below the confidence threshold — or flagged urgent — lands here with its reasoning
spelled out. A planner can approve as-is, edit the quantity, or reject with a reason."

Actually click **Approve edited** or **Reject** on one item.

"Notice this one's marked urgent — that's a separate signal from confidence. It means
on-hand stock will run out before the next reorder arrives, which is exactly the moment
in-store pickup promises would break and stores would need to pull from another location.
I didn't build full order-routing for that — it's flagged so a human handles it, not
silently auto-approved."

"And the confidence threshold itself isn't hardcoded — it's this slider."

Drag the sidebar slider from 0.70 to 0.75 live.

"Watch — the spike SKU, which was sitting right at the boundary, just moved into the
review queue. That's a deliberate design choice: how much autonomy the agent gets is a
human's call, not something baked into the code."

## 5. Show the audit trail (20 sec)

Switch to **Audit trail** tab.

"Every decision a planner makes gets logged. In a full version, these corrections would
feed back into the agent's thresholds over time — that feedback loop is designed for in
my workflow doc, even though it's not wired up in this prototype."

## 6. Close with honesty (30 sec)

"This is a prototype, not a production system — no auth, no real ERP integration, no
persistence beyond the session, and the thresholds are hand-tuned against this dataset,
not validated against real retail behavior. It also doesn't model per-store inventory or
full fulfillment routing — that's a different system, so I flagged the signal that would
trigger those workarounds instead of simulating them. All of that's written up in the
decisions README, along with the reasoning behind each design choice. Thanks for watching."

---

## Recording checklist

- [ ] App running locally or on the deployed URL, confidence slider reset to 0.70
- [ ] Browser window sized so the sidebar + tabs are both visible
- [ ] Have one item ready in the review queue to actually click Approve/Reject on
- [ ] Know which SKU you'll drag the slider to flip (APP-1042 at 0.70 → 0.75)
- [ ] Say the URL out loud once if it's deployed, so it's captured in the recording
