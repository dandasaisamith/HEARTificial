"""Rollup module: account risk aggregation and group formation for TRACE-FX.

Account risk uses noisy-OR: 1 - prod(1 - p_i) where p_i = clip(net_points/100).
Groups are connected components over EVIDENCE LINKS, not raw graph connectivity.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import networkx as nx
import pandas as pd

from .types import Decision, Evidence, Group

log = logging.getLogger(__name__)


def accounts(decisions: dict[str, Decision], df: pd.DataFrame) -> pd.DataFrame:
    """Roll up per-account risk from per-account decisions.

    Args:
        decisions: Account-level decisions from gate.decide().
        df: Canonical transaction DataFrame.

    Returns:
        DataFrame with columns: account_id, label, risk, net_points, alert_ts.
    """
    rows = []
    for acc, dec in decisions.items():
        rows.append({
            "account_id": acc,
            "label": dec.label,
            "risk": dec.risk,
            "net_points": dec.net_points,
            "alert_ts": dec.alert_ts,
        })

    if not rows:
        return pd.DataFrame(columns=["account_id", "label", "risk", "net_points", "alert_ts"])

    result = pd.DataFrame(rows)
    result = result.sort_values("risk", ascending=False).reset_index(drop=True)
    return result


def groups(evidence: list[Evidence], decisions: dict[str, Decision]) -> list[Group]:
    """Form suspicious groups from connected components over evidence links.

    Groups are NOT based on raw graph connectivity — only on shared evidence
    between accounts. This prevents shared infrastructure from creating
    giant false groups.

    Args:
        evidence: All Evidence objects from motifs.find_all().
        decisions: Account-level decisions from gate.decide().

    Returns:
        List of Group objects.
    """
    # Build an adjacency structure: account -> connected accounts via evidence
    evidence_graph = nx.Graph()

    for ev in evidence:
        accs = list(ev.accounts)
        for i in range(len(accs)):
            for j in range(i + 1, len(accs)):
                if not evidence_graph.has_edge(accs[i], accs[j]):
                    evidence_graph.add_edge(accs[i], accs[j], evidence_types=[])
                evidence_graph[accs[i]][accs[j]]["evidence_types"].append(ev.type)

    # Connected components = groups
    result_groups = []

    for component_idx, component in enumerate(
        nx.connected_components(evidence_graph), start=1
    ):
        if len(component) < 2:
            continue

        # Get all evidence types for this group
        group_evidence_types: set[str] = set()
        for ev in evidence:
            if any(acc in component for acc in ev.accounts):
                group_evidence_types.add(ev.type)

        # Group risk: noisy-OR over member account risks
        member_risks = [
            decisions[acc].risk
            for acc in component
            if acc in decisions
        ]
        group_risk = _noisy_or(member_risks)

        # Shape classification
        shape = _classify_shape(group_evidence_types, len(component))

        # Summary
        highest_label = "LEGIT"
        for acc in component:
            if acc in decisions:
                lbl = decisions[acc].label
                if lbl == "FRAUD":
                    highest_label = "FRAUD"
                    break
                elif lbl == "REVIEW" and highest_label != "FRAUD":
                    highest_label = "REVIEW"

        summary = (
            f"{len(component)} accounts, "
            f"evidence: {', '.join(sorted(group_evidence_types))}, "
            f"group risk: {group_risk:.2f}, "
            f"decision: {highest_label}"
        )

        result_groups.append(Group(
            group_id=f"G{component_idx:03d}",
            accounts=tuple(sorted(component)),
            evidence_types=tuple(sorted(group_evidence_types)),
            risk=round(group_risk, 4),
            shape=shape,
            summary=summary,
        ))

    # Sort groups by risk descending
    result_groups.sort(key=lambda g: g.risk, reverse=True)
    return result_groups


def _noisy_or(probabilities: list[float]) -> float:
    """Compute noisy-OR combination: 1 - prod(1 - p_i)."""
    if not probabilities:
        return 0.0
    result = 1.0
    for p in probabilities:
        result *= (1.0 - max(0.0, min(1.0, p)))
    return round(1.0 - result, 4)


def _classify_shape(evidence_types: set[str], n_accounts: int) -> str:
    """Classify the structural shape of a fraud group."""
    if "pass_through" in evidence_types and n_accounts <= 6:
        return "chain"
    elif "sequence_cohort" in evidence_types and n_accounts >= 4:
        return "cohort"
    elif "common_sink" in evidence_types and "shared_device" in evidence_types:
        return "star_mule"
    elif len(evidence_types) >= 3:
        return "mixed"
    elif "common_sink" in evidence_types:
        return "star_mule"
    else:
        return "mixed"
