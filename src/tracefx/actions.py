"""Actions module — deterministic action recommendations for TRACE-FX.

No LLM. No randomness. Actions are deterministic based on label and evidence.
"""

from __future__ import annotations

from .types import Decision, Group


def recommend(decision_or_group: Decision | Group) -> str:
    """Recommend an action for a Decision or Group.

    Args:
        decision_or_group: A Decision or Group object.

    Returns:
        A deterministic action string.
    """
    if isinstance(decision_or_group, Group):
        return _group_action(decision_or_group)
    return _decision_action(decision_or_group)


def _decision_action(decision: Decision) -> str:
    """Return action string for a Decision."""
    return recommend_for_label(
        decision.label,
        n_structural=len([
            line for line in decision.ledger
            if line.source in ("shared_device", "common_sink", "pass_through", "sequence_cohort", "burst")
        ]),
        structural_types=set(
            line.source for line in decision.ledger
            if line.source in ("shared_device", "common_sink", "pass_through", "sequence_cohort", "burst")
        ),
    )


def _group_action(group: Group) -> str:
    """Return action string for a Group."""
    types = set(group.evidence_types)
    parts = []

    if group.risk >= 0.6:
        parts.append("HOLD all group member accounts pending analyst review.")
        parts.append("ESCALATE to fraud operations team.")
    else:
        parts.append("FLAG group for analyst review.")

    if "common_sink" in types:
        parts.append("FREEZE common destination wallet pending investigation.")
    if "shared_device" in types:
        parts.append("BLOCK shared device from further transactions.")
    parts.append("NOTIFY compliance officer.")

    return " ".join(parts)


def recommend_for_label(
    label: str,
    n_structural: int = 0,
    structural_types: set | None = None,
) -> str:
    """Return deterministic action for a given decision label.

    Args:
        label: FRAUD | REVIEW | LEGIT
        n_structural: Number of independent structural evidence types.
        structural_types: Set of structural type names present.

    Returns:
        Action string.
    """
    if structural_types is None:
        structural_types = set()

    if label == "FRAUD":
        parts = ["HOLD transaction.", "ESCALATE to fraud operations."]
        if "common_sink" in structural_types:
            parts.append("FREEZE common destination.")
        if "shared_device" in structural_types:
            parts.append("CONTAIN shared device.")
        return " ".join(parts)

    elif label == "REVIEW":
        parts = ["STEP-UP AUTHENTICATION required."]
        parts.append("QUEUE for analyst review within 4 hours.")
        return " ".join(parts)

    else:  # LEGIT
        return "NO ACTION — transaction cleared."
