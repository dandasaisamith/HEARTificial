"""Decision gate for TRACE-FX — implements the frozen FRAUD/REVIEW/LEGIT rule.

FRAUD requires BOTH:
  1. net_points >= gate.fraud_net (default 60)
  2. >= gate.fraud_min_structural_types (default 2) independent structural types

REVIEW: net_points >= gate.review_net (default 30) OR strong single structural signal

LEGIT: otherwise

Behaviour score alone NEVER produces FRAUD.
"""

from __future__ import annotations

import logging

import pandas as pd

from .types import Decision, Evidence, LedgerLine
from .ledger import STRUCTURAL_TYPES

log = logging.getLogger(__name__)


def decide(
    ledger: dict[str, list[LedgerLine]],
    evidence: list[Evidence],
    cfg: dict,
) -> dict[str, Decision]:
    """Apply the frozen decision gate to produce FRAUD/REVIEW/LEGIT decisions.

    Args:
        ledger: Per-account ledger from ledger.build().
        evidence: All Evidence objects from motifs.find_all().
        cfg: Configuration dict.

    Returns:
        Dict mapping account_id -> Decision.
    """
    gate_cfg = cfg["gate"]
    fraud_net = gate_cfg["fraud_net"]
    min_structural = gate_cfg["fraud_min_structural_types"]
    review_net = gate_cfg["review_net"]

    # Build per-account evidence type index
    account_structural_types: dict[str, set[str]] = {}
    account_evidence_satisfied_at: dict[str, str] = {}

    for ev in evidence:
        for acc in ev.accounts:
            if acc not in account_structural_types:
                account_structural_types[acc] = set()
            if ev.type in STRUCTURAL_TYPES:
                account_structural_types[acc].add(ev.type)
                # Track earliest satisfied_at per account
                if acc not in account_evidence_satisfied_at:
                    account_evidence_satisfied_at[acc] = ev.satisfied_at
                else:
                    if ev.satisfied_at < account_evidence_satisfied_at[acc]:
                        account_evidence_satisfied_at[acc] = ev.satisfied_at

    # All accounts that appear in ledger OR evidence
    all_accounts = set(ledger.keys()) | set(account_structural_types.keys())

    decisions: dict[str, Decision] = {}

    for acc in all_accounts:
        lines = ledger.get(acc, [])
        net_points = sum(line.points for line in lines)
        structural_types = account_structural_types.get(acc, set())
        n_structural = len(structural_types)

        # Determine causal alert_ts
        # alert_ts = first moment when gate conditions were met
        satisfied_at = account_evidence_satisfied_at.get(acc, "")

        # Apply gate
        if net_points >= fraud_net and n_structural >= min_structural:
            label = "FRAUD"
            alert_ts = satisfied_at
        elif net_points >= review_net or (n_structural >= 1 and net_points > 0):
            label = "REVIEW"
            alert_ts = satisfied_at
        else:
            label = "LEGIT"
            alert_ts = ""

        # Behaviour alone cannot produce FRAUD (safety check)
        if label == "FRAUD":
            non_behaviour_points = sum(
                line.points for line in lines
                if line.source not in ("behaviour_anomaly",)
            )
            if non_behaviour_points < review_net:
                # Even with behaviour, structural evidence is weak
                label = "REVIEW"

        # Risk score: clip net_points to [0, 100] -> [0, 1]
        risk = max(0.0, min(1.0, net_points / 100.0))

        # Action
        from .actions import recommend_for_label
        action = recommend_for_label(label, n_structural, structural_types)

        # Ensure at least one ledger line
        if not lines:
            lines = [LedgerLine(
                source="no_evidence",
                points=0.0,
                text="No structural evidence found; transaction appears legitimate.",
                tx_ids=(),
            )]

        decisions[acc] = Decision(
            tx_id=acc,  # using account_id as the key
            label=label,
            net_points=round(net_points, 2),
            risk=round(risk, 4),
            ledger=lines,
            action=action,
            alert_ts=alert_ts,
        )

    return decisions
