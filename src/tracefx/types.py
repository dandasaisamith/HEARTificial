"""Frozen data contracts for TRACE-FX.

DO NOT edit without explicit approval — types.py is frozen per AGENTS.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class Evidence:
    """A single structural fraud motif detection result."""

    type: str            # shared_device | common_sink | pass_through | sequence_cohort | burst
    accounts: tuple
    tx_ids: tuple
    first_ts: str
    last_ts: str
    satisfied_at: str    # ts when this evidence's condition first became true (causal)
    strength: float      # 0..1
    detail: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "accounts", tuple(self.accounts))
        object.__setattr__(self, "tx_ids", tuple(self.tx_ids))
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(f"Evidence.strength must be in [0,1], got {self.strength}")


@dataclass(frozen=True)
class LedgerLine:
    """One positive or negative evidence line in the decision ledger."""

    source: str          # e.g. "common_sink", "tenure_over_1y"
    points: float        # positive = evidence, negative = exculpatory
    text: str            # human sentence citing tx ids / timestamps
    tx_ids: tuple = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "tx_ids", tuple(self.tx_ids))


@dataclass
class Decision:
    """Per-transaction fraud decision with full evidence chain."""

    tx_id: str
    label: str           # FRAUD | REVIEW | LEGIT
    net_points: float
    risk: float          # 0..1
    ledger: list[LedgerLine]
    action: str
    alert_ts: str        # causal time the gate conditions were first met


@dataclass
class Group:
    """A suspicious account group identified by connected evidence."""

    group_id: str
    accounts: tuple
    evidence_types: tuple
    risk: float
    shape: str           # star_mule | chain | cohort | mixed
    summary: str


@dataclass
class Result:
    """Complete pipeline output — the public contract consumed by UI/CLI/eval."""

    tx: pd.DataFrame            # per-tx scores + labels
    accounts: pd.DataFrame      # per-account risk + label
    groups: list[Group]
    evidence: list[Evidence]
    decisions: dict[str, Decision]   # tx_id -> Decision
    graph: dict                      # nodes/edges json for the ring view
    metrics: dict
    degraded: list[str]              # names of stages that failed soft
    quality: dict
    capabilities: dict               # which motifs are active given columns present
