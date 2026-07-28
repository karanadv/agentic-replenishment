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

"This is 26 weeks of synthetic sales, inventory, and supplier data across 15 SKUs.
Every row here is a recommendation the agent already computed — quantity, confidence,
and whether it's auto-approved or held for review."

Point at the sorted-by-confidence table.

"Notice it's sorted by confidence — the ones the system is least sure about float to
the top automatically."

## 3. Walk through the three edge cases (90 sec)

Use the SKU selector to show each chart while narrating:

**Demand spike — APP-1042:**
"This jacket saw a 4x demand jump in the last three weeks — a viral video, in this case.
A naive system might read that as the new normal and massively over-order. Instead, the
agent flags it as a likely spike, discounts it back to the 8-week baseline, and drops its
own confidence to 70% instead of pretending it's sure."

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
below the confidence threshold — right now set at 70% — lands here with its reasoning
spelled out. A planner can approve as-is, edit the quantity, or reject with a reason."

Actually click **Approve edited** or **Reject** on one item.

"And that threshold isn't hardcoded — it's this slider."

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
not validated against real retail behavior. All of that's written up in the decisions
README, along with the reasoning behind each design choice. Thanks for watching."

---

## Recording checklist

- [ ] App running locally or on the deployed URL, confidence slider reset to 0.70
- [ ] Browser window sized so the sidebar + tabs are both visible
- [ ] Have one item ready in the review queue to actually click Approve/Reject on
- [ ] Know which SKU you'll drag the slider to flip (APP-1042 at 0.70 → 0.75)
- [ ] Say the URL out loud once if it's deployed, so it's captured in the recording
