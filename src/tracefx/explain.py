"""Explanation chain generator for TRACE-FX.

Produces human-readable decision chains from Group or Decision objects.
Template-based, deterministic, no LLM.
"""

from __future__ import annotations

from .types import Decision, Group


def chain(group_or_decision: Group | Decision) -> str:
    """Generate a human-readable explanation chain.

    Args:
        group_or_decision: A Group or Decision to explain.

    Returns:
        Human-readable explanation string.
    """
    if isinstance(group_or_decision, Group):
        return _explain_group(group_or_decision)
    return _explain_decision(group_or_decision)


def _explain_group(group: Group) -> str:
    """Explain a fraud group."""
    lines = [
        f"FRAUD GROUP {group.group_id}",
        f"Accounts involved: {', '.join(group.accounts[:10])}{'...' if len(group.accounts) > 10 else ''}",
        f"Evidence types: {', '.join(group.evidence_types)}",
        f"Group risk: {group.risk:.2f}",
        f"Structure: {group.shape}",
        "",
        group.summary,
    ]
    return "\n".join(lines)


def _explain_decision(decision: Decision) -> str:
    """Explain a per-account decision."""
    lines = [
        f"DECISION: {decision.label}",
        f"Account: {decision.tx_id}",
        f"Net points: {decision.net_points:.1f}",
        f"Risk: {decision.risk:.4f}",
        f"Action: {decision.action}",
        "",
        "EVIDENCE LEDGER:",
    ]

    positive = [l for l in decision.ledger if l.points > 0]
    negative = [l for l in decision.ledger if l.points < 0]

    if positive:
        lines.append("  SUSPICIOUS FACTORS:")
        for l in positive:
            lines.append(f"    {l.text}")

    if negative:
        lines.append("  EXCULPATORY FACTORS (why not FRAUD):")
        for l in negative:
            lines.append(f"    {l.text}")

    if not positive and not negative:
        lines.append("  No evidence — transaction appears legitimate.")

    if decision.alert_ts:
        lines.append(f"\nCausal alert time: {decision.alert_ts}")

    return "\n".join(lines)
