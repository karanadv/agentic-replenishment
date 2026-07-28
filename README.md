# Agentic Replenishment — Prototype

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

This opens the dashboard at `http://localhost:8501`. Note: this prototype's engine logic
was fully tested (see `engine/` — every function was run and its output checked against
the three known edge cases), but the Streamlit UI itself hasn't been runtime-tested in
this build environment (no network access to install Streamlit here) — run it locally
first before recording your demo, in case any UI-layer issue needs a quick fix.

## Deploy (for your live URL)

1. Push this folder to a new GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. "New app" → pick your repo → main file path `app.py` → Deploy.
4. You'll get a public URL like `https://your-app-name.streamlit.app`.

## The three built-in edge cases

- **APP-1042** (Trail Runner Jacket) — live demand spike, still elevated as of "today"
- **FTW-3301 / 3302 / 3350** (footwear, supplier SUP-03) — supplier lead time jumped 21 → 45 days
- **ACC-9981 / 9982** (replacement buckles) — long-tail SKUs with too little history to trust

Try the confidence slider in the sidebar — dragging it past ~0.70 will flip the spike SKU
between auto-approved and needs-review live, which is a good moment to show in your Loom.
