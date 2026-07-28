"""
ESCALATE stage.

Routes each draft PO to one of two lanes. Three things decide the lane,
in priority order:

  1. AUTONOMY_FLOOR  — a hard limit the planner cannot lower. Below it,
                       nothing auto-approves, at any slider setting.
  2. urgent flag     — operational risks that aren't forecast-accuracy
                       questions and shouldn't be settled by a confidence dial.
  3. confidence_threshold — the tunable slider, which governs everything
                       in the band between the floor and full confidence.

The floor closes an asymmetry in the earlier design: the urgent flag was
un-overridable, but the agent's own declaration that it lacks the data to
judge a SKU ("sold in only 3 of the last 12 weeks") was fully overridable —
dragging the slider to 0.40 auto-approved it with no human ever seeing it.
If the argument for the urgent carve-out is that the agent shouldn't be able
to wave past things it has flagged as beyond its competence, then epistemic
uncertainty is the stronger case, not the weaker one: a stockout is something
the agent computed correctly, while sparse history means it genuinely does
not know. A trust layer that can be told to trust itself completely is not a
trust layer.
"""

# Calibrated against the confidence model in decide.py: a single uncertainty
# signal leaves a SKU at 0.70-0.75, so this floor does not catch routine
# flags. It catches the sparse-history case (0.40) and anything that has
# stacked two or more independent uncertainty signals.
AUTONOMY_FLOOR = 0.50


def route(draft: dict, confidence_threshold: float) -> str:
    """Returns 'auto' or 'needs_review'.

    Note this collapses several distinct reasons for review into one lane —
    a low-confidence item and a compound-risk item are indistinguishable to
    any caller. See route_with_reason() and the decisions README.
    """
    lane, _ = route_with_reason(draft, confidence_threshold)
    return lane


def route_with_reason(draft: dict, confidence_threshold: float) -> tuple:
    """Same routing, but also returns which rule fired — so the UI and the
    audit trail can show a planner why an item is in front of them."""
    # Missing confidence is a programming error and should fail loudly.
    # Missing 'urgent' defaults to False, which is the unsafe direction, so
    # it is stated explicitly rather than left to an implicit .get() default.
    confidence = draft["confidence"]
    urgent = draft.get("urgent", False)

    if confidence < AUTONOMY_FLOOR:
        return "needs_review", "below_autonomy_floor"
    if urgent:
        return "needs_review", "urgent_operational_risk"
    if confidence < confidence_threshold:
        return "needs_review", "below_planner_threshold"
    return "auto", "within_autonomy"
