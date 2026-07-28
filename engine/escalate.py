"""
ESCALATE stage.

Routes each draft PO to one of two lanes based on a single tunable
confidence threshold (this is the parameter the planner controls,
and the thing we deliberately left as "decide once you see the data"
in the design phase — surfacing it as a UI control rather than a
hardcoded constant is the point).
"""


def route(draft: dict, confidence_threshold: float) -> str:
    """Returns 'auto' or 'needs_review'."""
    if draft["confidence"] < confidence_threshold:
        return "needs_review"
    return "auto"
