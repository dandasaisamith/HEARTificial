"""Pipeline orchestration for TRACE-FX.

Public interface: pipeline.run(df, cfg) -> Result

Every stage is wrapped in _safe() for fail-soft behaviour.
Failures append to Result.degraded and use fallbacks.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

import networkx as nx
import pandas as pd

from . import schema as schema_mod
from . import features as features_mod
from . import baseline as baseline_mod
from . import graph as graph_mod
from . import motifs as motifs_mod
from . import ledger as ledger_mod
from . import gate as gate_mod
from . import rollup as rollup_mod
from .types import Decision, Evidence, Group, LedgerLine, Result

log = logging.getLogger(__name__)


def _safe(
    name: str,
    fn: Callable,
    fallback: Any,
    degraded: list[str],
    *args,
    **kwargs,
) -> Any:
    """Run a pipeline stage, catching all exceptions.

    On failure: logs the error, appends stage name to degraded, returns fallback.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        log.error("Stage %r failed: %s", name, exc, exc_info=True)
        degraded.append(name)
        return fallback


def run(df: pd.DataFrame, cfg: dict) -> Result:
    """Run the complete TRACE-FX pipeline on a transaction DataFrame.

    Args:
        df: Canonical transaction DataFrame (from schema.load()).
        cfg: Configuration dict (from config.load()).

    Returns:
        Result containing all pipeline outputs.

    This is the ONLY public boundary. All consumers (UI, CLI, evaluate)
    must call this function and consume Result.
    """
    t0 = time.perf_counter()
    degraded: list[str] = []

    # -----------------------------------------------------------------
    # 0. Capability detection
    # -----------------------------------------------------------------
    caps = schema_mod.capabilities(df)
    quality = schema_mod.quality_report(df)

    # -----------------------------------------------------------------
    # 1. Feature engineering
    # -----------------------------------------------------------------
    feat = _safe(
        "features",
        features_mod.build,
        pd.DataFrame(index=df.index),
        degraded,
        df, cfg,
    )

    # -----------------------------------------------------------------
    # 2. Behaviour scoring
    # -----------------------------------------------------------------
    if feat.empty:
        behaviour = pd.Series(0.0, index=df.index, name="behaviour_score")
        degraded.append("baseline_fallback")
    else:
        behaviour = _safe(
            "baseline",
            baseline_mod.score,
            pd.Series(0.0, index=df.index, name="behaviour_score"),
            degraded,
            feat, cfg,
        )

    # -----------------------------------------------------------------
    # 3. Entity graph
    # -----------------------------------------------------------------
    G = _safe(
        "graph",
        graph_mod.build,
        nx.MultiGraph(),
        degraded,
        df, cfg,
    )

    # -----------------------------------------------------------------
    # 4. Motif detection
    # -----------------------------------------------------------------
    evidence: list[Evidence] = _safe(
        "motifs",
        motifs_mod.find_all,
        [],
        degraded,
        df, G, cfg,
    )

    if "motifs" in degraded:
        # If motifs failed, cap at REVIEW
        log.warning("Motifs stage failed; capping decisions at REVIEW")

    # -----------------------------------------------------------------
    # 5. Evidence ledger
    # -----------------------------------------------------------------
    ledger: dict[str, list[LedgerLine]] = _safe(
        "ledger",
        ledger_mod.build,
        {},
        degraded,
        df, behaviour, evidence, cfg,
    )

    # Ensure every account that appears in transactions has at least a minimal ledger
    for payer in df["payer_id"].unique():
        if payer not in ledger:
            ledger[payer] = [LedgerLine(
                source="no_evidence",
                points=0.0,
                text="No suspicious patterns detected for this account.",
                tx_ids=(),
            )]

    # -----------------------------------------------------------------
    # 6. Gate decision
    # -----------------------------------------------------------------
    decisions_raw: dict[str, Decision] = _safe(
        "gate",
        gate_mod.decide,
        {},
        degraded,
        ledger, evidence, cfg,
    )

    # If motifs degraded, ensure no FRAUD decisions
    if "motifs" in degraded:
        decisions_raw = {
            acc: Decision(
                tx_id=dec.tx_id,
                label=min(dec.label, "REVIEW", key=lambda x: ["FRAUD", "REVIEW", "LEGIT"].index(x)),
                net_points=dec.net_points,
                risk=min(dec.risk, 0.5),
                ledger=dec.ledger,
                action=dec.action,
                alert_ts=dec.alert_ts,
            )
            for acc, dec in decisions_raw.items()
        }

    # -----------------------------------------------------------------
    # 7. Account rollup
    # -----------------------------------------------------------------
    accounts_df: pd.DataFrame = _safe(
        "rollup_accounts",
        rollup_mod.accounts,
        pd.DataFrame(columns=["account_id", "label", "risk", "net_points", "alert_ts"]),
        degraded,
        decisions_raw, df,
    )

    # -----------------------------------------------------------------
    # 8. Group rollup
    # -----------------------------------------------------------------
    groups_list: list[Group] = _safe(
        "rollup_groups",
        rollup_mod.groups,
        [],
        degraded,
        evidence, decisions_raw,
    )

    # -----------------------------------------------------------------
    # 9. Per-transaction labels and tx-level decisions
    # -----------------------------------------------------------------
    tx_df = _build_tx_df(df, behaviour, decisions_raw, evidence)

    tx_decisions: dict[str, Decision] = {}
    for row in tx_df.itertuples():
        tx_id = row.tx_id
        acc_dec = decisions_raw.get(row.payer_id)
        if acc_dec:
            tx_decisions[tx_id] = Decision(
                tx_id=tx_id,
                label=row.tx_label,
                net_points=acc_dec.net_points,
                risk=acc_dec.risk,
                ledger=acc_dec.ledger,
                action=acc_dec.action,
                alert_ts=acc_dec.alert_ts,
            )

    # -----------------------------------------------------------------
    # 10. Graph JSON for visualization
    # -----------------------------------------------------------------
    graph_json = _safe(
        "graph_json",
        _build_graph_json,
        {"nodes": [], "edges": []},
        degraded,
        df, evidence, decisions_raw,
    )

    # -----------------------------------------------------------------
    # 11. Metrics
    # -----------------------------------------------------------------
    elapsed = time.perf_counter() - t0
    n_fraud = int((accounts_df["label"] == "FRAUD").sum()) if not accounts_df.empty else 0
    n_review = int((accounts_df["label"] == "REVIEW").sum()) if not accounts_df.empty else 0
    n_legit = int((accounts_df["label"] == "LEGIT").sum()) if not accounts_df.empty else 0

    metrics = {
        "total_transactions": len(df),
        "total_accounts": int(df["payer_id"].nunique()),
        "fraud_accounts": n_fraud,
        "review_accounts": n_review,
        "legit_accounts": n_legit,
        "evidence_items": len(evidence),
        "groups": len(groups_list),
        "elapsed_s": round(elapsed, 3),
        "degraded_stages": list(degraded),
    }

    log.info(
        "Pipeline complete in %.2fs: %d fraud, %d review, %d legit accounts",
        elapsed, n_fraud, n_review, n_legit,
    )

    return Result(
        tx=tx_df,
        accounts=accounts_df,
        groups=groups_list,
        evidence=evidence,
        decisions=tx_decisions,
        graph=graph_json,
        metrics=metrics,
        degraded=degraded,
        quality=quality,
        capabilities=caps,
    )


def _build_tx_df(
    df: pd.DataFrame,
    behaviour: pd.Series,
    decisions: dict[str, Decision],
    evidence: list[Evidence],
) -> pd.DataFrame:
    """Build per-transaction DataFrame with scores and labels."""
    tx = df.copy()

    # Behaviour score
    bscore = behaviour.values if len(behaviour) == len(df) else [0.0] * len(df)
    tx["behaviour_score"] = bscore

    # Account-level label propagation
    tx["account_label"] = tx["payer_id"].map(
        {acc: dec.label for acc, dec in decisions.items()}
    ).fillna("LEGIT")

    tx["account_risk"] = tx["payer_id"].map(
        {acc: dec.risk for acc, dec in decisions.items()}
    ).fillna(0.0)

    # Evidence tx_ids: mark transactions that are directly in evidence
    evidence_tx_set: set[str] = set()
    for ev in evidence:
        evidence_tx_set.update(ev.tx_ids)

    tx["in_evidence"] = tx["tx_id"].isin(evidence_tx_set)

    # Tx-level label: FRAUD only if tx is in evidence for a FRAUD account
    fraud_accounts = {acc for acc, dec in decisions.items() if dec.label == "FRAUD"}

    def tx_label(row):
        in_ev = row["tx_id"] in evidence_tx_set
        acc_label = row["account_label"]
        if in_ev:
            return acc_label if acc_label in ("FRAUD", "REVIEW") else "LEGIT"
        else:
            if acc_label == "FRAUD":
                return "REVIEW"
            return "LEGIT"

    tx["tx_label"] = tx.apply(tx_label, axis=1)

    return tx


def _build_graph_json(
    df: pd.DataFrame,
    evidence: list[Evidence],
    decisions: dict[str, Decision],
) -> dict:
    """Build a compact graph JSON for the ring visualization."""
    nodes = {}
    edges = []

    for ev in evidence:
        # Add accounts
        for acc in ev.accounts:
            if acc not in nodes:
                dec = decisions.get(acc)
                label = dec.label if dec else "LEGIT"
                nodes[acc] = {
                    "id": acc,
                    "label": acc[-8:],
                    "type": "account",
                    "decision": label,
                    "risk": dec.risk if dec else 0.0,
                    "satisfied_at": ev.satisfied_at,
                }

        # Add evidence-specific nodes and edges
        if ev.type == "shared_device":
            device = ev.detail.get("device_id", "D_unknown")
            if device not in nodes:
                nodes[device] = {
                    "id": device,
                    "label": device[-8:],
                    "type": "device",
                    "decision": "EVIDENCE",
                    "risk": ev.strength,
                    "satisfied_at": ev.satisfied_at,
                }
            for acc in ev.accounts:
                edges.append({
                    "from": acc,
                    "to": device,
                    "type": "uses_device",
                    "satisfied_at": ev.satisfied_at,
                    "strength": ev.strength,
                })

        elif ev.type == "common_sink":
            sink = ev.detail.get("sink", "W_unknown")
            if sink not in nodes:
                nodes[sink] = {
                    "id": sink,
                    "label": sink[-8:],
                    "type": "wallet",
                    "decision": "SINK",
                    "risk": ev.strength,
                    "satisfied_at": ev.satisfied_at,
                }
            for acc in ev.accounts:
                if acc != sink:
                    edges.append({
                        "from": acc,
                        "to": sink,
                        "type": "common_sink",
                        "satisfied_at": ev.satisfied_at,
                        "strength": ev.strength,
                    })

        elif ev.type == "pass_through":
            accs = list(ev.accounts)
            for i in range(len(accs) - 1):
                edges.append({
                    "from": accs[i],
                    "to": accs[i+1],
                    "type": "pass_through",
                    "satisfied_at": ev.satisfied_at,
                    "strength": ev.strength,
                })

        elif ev.type in ("sequence_cohort", "burst"):
            accs = list(ev.accounts)
            for i in range(len(accs)):
                for j in range(i+1, min(i+3, len(accs))):
                    edges.append({
                        "from": accs[i],
                        "to": accs[j],
                        "type": ev.type,
                        "satisfied_at": ev.satisfied_at,
                        "strength": ev.strength,
                    })

    return {"nodes": list(nodes.values()), "edges": edges}


def result_to_json(result: Result) -> str:
    """Serialize a Result to JSON string (lossless for supported fields)."""
    def decision_to_dict(dec: Decision) -> dict:
        return {
            "tx_id": dec.tx_id,
            "label": dec.label,
            "net_points": dec.net_points,
            "risk": dec.risk,
            "action": dec.action,
            "alert_ts": dec.alert_ts,
            "ledger": [
                {"source": l.source, "points": l.points, "text": l.text, "tx_ids": list(l.tx_ids)}
                for l in dec.ledger
            ],
        }

    def evidence_to_dict(ev: Evidence) -> dict:
        return {
            "type": ev.type,
            "accounts": list(ev.accounts),
            "tx_ids": list(ev.tx_ids),
            "first_ts": ev.first_ts,
            "last_ts": ev.last_ts,
            "satisfied_at": ev.satisfied_at,
            "strength": ev.strength,
            "detail": ev.detail,
        }

    def group_to_dict(g: Group) -> dict:
        return {
            "group_id": g.group_id,
            "accounts": list(g.accounts),
            "evidence_types": list(g.evidence_types),
            "risk": g.risk,
            "shape": g.shape,
            "summary": g.summary,
        }

    data = {
        "tx": result.tx.to_dict(orient="records"),
        "accounts": result.accounts.to_dict(orient="records"),
        "groups": [group_to_dict(g) for g in result.groups],
        "evidence": [evidence_to_dict(e) for e in result.evidence],
        "decisions": {k: decision_to_dict(v) for k, v in result.decisions.items()},
        "graph": result.graph,
        "metrics": result.metrics,
        "degraded": result.degraded,
        "quality": result.quality,
        "capabilities": result.capabilities,
    }
    return json.dumps(data, default=str)


def result_from_json(json_str: str) -> Result:
    """Deserialize a Result from JSON string."""
    from .types import LedgerLine, Decision, Evidence, Group
    data = json.loads(json_str)

    tx = pd.DataFrame(data["tx"])
    accs = pd.DataFrame(data["accounts"])

    evidence = [
        Evidence(
            type=e["type"],
            accounts=tuple(e["accounts"]),
            tx_ids=tuple(e["tx_ids"]),
            first_ts=e["first_ts"],
            last_ts=e["last_ts"],
            satisfied_at=e["satisfied_at"],
            strength=e["strength"],
            detail=e.get("detail", {}),
        )
        for e in data["evidence"]
    ]

    groups_list = [
        Group(
            group_id=g["group_id"],
            accounts=tuple(g["accounts"]),
            evidence_types=tuple(g["evidence_types"]),
            risk=g["risk"],
            shape=g["shape"],
            summary=g["summary"],
        )
        for g in data["groups"]
    ]

    decisions = {
        k: Decision(
            tx_id=v["tx_id"],
            label=v["label"],
            net_points=v["net_points"],
            risk=v["risk"],
            action=v["action"],
            alert_ts=v["alert_ts"],
            ledger=[
                LedgerLine(
                    source=l["source"],
                    points=l["points"],
                    text=l["text"],
                    tx_ids=tuple(l["tx_ids"]),
                )
                for l in v["ledger"]
            ],
        )
        for k, v in data["decisions"].items()
    }

    return Result(
        tx=tx,
        accounts=accs,
        groups=groups_list,
        evidence=evidence,
        decisions=decisions,
        graph=data.get("graph", {"nodes": [], "edges": []}),
        metrics=data.get("metrics", {}),
        degraded=data.get("degraded", []),
        quality=data.get("quality", {}),
        capabilities=data.get("capabilities", {}),
    )
