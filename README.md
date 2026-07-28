# Agentic Replenishment — Prototype

**Live app:** https://agentic-replenishment-cfz5mznsmvyujuc692qt9e.streamlit.app/

A rule-based sense → decide → act → escalate pipeline for retail replenishment,
with a Streamlit dashboard as the trust & control layer.

## Structure

```
├── data/                     # synthetic sales/inventory/supplier data (26 weeks, 15 SKUs)
├── engine/
│   ├── sense.py               # loads data, computes rolling averages + anomaly signals
│   ├── decide.py               # recommendation + confidence score + reasoning (no LLM — explainable rules)
│   ├── act.py                    # drafts a PO with cost, tags, and reasoning attached
│   └── escalate.py                # routes to auto-approve vs. needs-review based on a tunable threshold
├── app.py                     # Streamlit dashboard: overview, review queue, audit trail
└── requirements.txt
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

This opens the dashboard at `http://localhost:8501`. The engine logic in `engine/` is
verified end-to-end against all four embedded edge cases; the app is also deployed and
running at the URL below. Note that the engine was updated after the initial deployment
(see decisions 5 and 5b in the decisions README) — if the live app is showing older
numbers, push the current `engine/` files to GitHub and reboot the app.

## Deploy (for your live URL)

**Already deployed:** https://agentic-replenishment-cfz5mznsmvyujuc692qt9e.streamlit.app/

To redeploy or update after changes:
1. Push updated files to the GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. Find the app under "Manage app" and it will auto-redeploy on new commits, or click "Reboot app."

## The three built-in edge cases

- **APP-1042** (Trail Runner Jacket) — live demand spike, still elevated as of "today"
- **FTW-3301 / 3302 / 3350** (footwear, supplier SUP-03) — supplier lead time jumped 21 → 45 days
- **ACC-9981 / 9982** (replacement buckles) — long-tail SKUs with too little history to trust

Try the confidence slider in the sidebar — dragging it past ~0.70 will flip the spike SKU
between auto-approved and needs-review live, which is a good moment to show in your Loom.
