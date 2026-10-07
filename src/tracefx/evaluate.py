"""Evaluation module for TRACE-FX.

Produces honest metrics from real pipeline runs.
NEVER invents numbers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from . import config as config_mod
from . import schema as schema_mod
from .pipeline import run as pipeline_run

log = logging.getLogger(__name__)


def report(
    seed_paths: list[tuple[str, str]],  # list of (csv_path, truth_path)
    cfg: dict,
    out_dir: Optional[str | Path] = None,
) -> pd.DataFrame:
    """Generate evaluation metrics for all seeds.

    Args:
        seed_paths: List of (csv_path, truth_path) tuples.
        cfg: Configuration dict.
        out_dir: Optional directory to save reports.

    Returns:
        DataFrame with metrics per seed.
    """
    rows = []

    for csv_path, truth_path in seed_paths:
        log.info("Evaluating %s", csv_path)
        try:
            row = _evaluate_seed(csv_path, truth_path, cfg)
            rows.append(row)
        except Exception as exc:
            log.error("Evaluation failed for %s: %s", csv_path, exc, exc_info=True)
            rows.append({"seed_file": str(csv_path), "error": str(exc)})

    df = pd.DataFrame(rows)

    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "eval_results.csv", index=False)
        log.info("Evaluation results saved to %s", out_dir / "eval_results.csv")

    return df


def _evaluate_seed(csv_path: str, truth_path: str, cfg: dict) -> dict:
    """Evaluate TRACE-FX on one seed."""
    # Load data
    df = schema_mod.load(csv_path)
    with open(truth_path, "r") as f:
        truth = json.load(f)

    seed = truth.get("seed", "unknown")

    # Run pipeline
    result = pipeline_run(df, cfg)

    # Extract predictions
    accs = result.accounts.set_index("account_id") if not result.accounts.empty else pd.DataFrame()

    # ----- FP on legitimate high-value transactions -----
    hv_tx_ids = set(truth.get("high_value_legit_tx_ids", []))
    hv_fraud_only = 0
    hv_fraud_or_review = 0

    if hv_tx_ids and not result.tx.empty:
        hv_txs = result.tx[result.tx["tx_id"].isin(hv_tx_ids)]
        if not hv_txs.empty:
            hv_fraud_only = int((hv_txs["tx_label"] == "FRAUD").sum())
            hv_fraud_or_review = int(hv_txs["tx_label"].isin(["FRAUD", "REVIEW"]).sum())

    # ----- Ring recall -----
    rings = truth.get("rings", [])
    n_rings = len(rings)
    n_full = 0
    n_partial = 0
    n_missed = 0

    for ring in rings:
        ring_accounts = set(ring.get("accounts", []))
        if not ring_accounts:
            continue

        # Find the group with most overlap
        best_overlap = 0
        for group in result.groups:
            group_accs = set(group.accounts)
            overlap = len(ring_accounts & group_accs) / len(ring_accounts)
            best_overlap = max(best_overlap, overlap)

        if best_overlap >= 0.80:
            n_full += 1
        elif best_overlap >= 0.40:
            n_partial += 1
        else:
            n_missed += 1

    # ----- Precision / account-level -----
    fraud_tx_ids = set(truth.get("is_fraud_tx_ids", []))
    ring_accounts = set()
    for ring in rings:
        if ring.get("type") == "R1":  # only R1 is expected FRAUD
            ring_accounts.update(ring.get("accounts", []))

    if not accs.empty and ring_accounts:
        pred_fraud_accs = set(accs[accs["label"] == "FRAUD"].index)
        pred_review_accs = set(accs[accs["label"] == "REVIEW"].index)

        tp_fraud = len(pred_fraud_accs & ring_accounts)
        fp_fraud = len(pred_fraud_accs - ring_accounts)
        precision_fraud = tp_fraud / max(len(pred_fraud_accs), 1)
        recall_fraud = tp_fraud / max(len(ring_accounts), 1)

        # precision@10: among top 10 by risk, how many are true fraud?
        top10 = accs.nlargest(10, "risk").index.tolist() if len(accs) >= 10 else accs.index.tolist()
        p_at_10 = len(set(top10) & ring_accounts) / max(len(top10), 1)

        top50 = accs.nlargest(50, "risk").index.tolist() if len(accs) >= 50 else accs.index.tolist()
        p_at_50 = len(set(top50) & ring_accounts) / max(len(top50), 1)

        # PR-AUC approximation
        all_risks = accs["risk"].values
        all_labels = accs.index.map(lambda x: 1 if x in ring_accounts else 0).values
        pr_auc = _approx_pr_auc(all_risks, all_labels)
    else:
        precision_fraud = recall_fraud = p_at_10 = p_at_50 = pr_auc = float("nan")
        fp_fraud = 0

    # ----- Latency -----
    elapsed = result.metrics.get("elapsed_s", float("nan"))
    n_txs = result.metrics.get("total_transactions", len(df))
    latency_per_tx_ms = (elapsed / max(n_txs, 1)) * 1000

    return {
        "seed_file": Path(csv_path).stem,
        "seed": seed,
        "n_transactions": n_txs,
        "n_accounts": result.metrics.get("total_accounts", 0),
        "n_fraud_accounts": result.metrics.get("fraud_accounts", 0),
        "n_review_accounts": result.metrics.get("review_accounts", 0),
        "n_groups": len(result.groups),
        "ring_full": n_full,
        "ring_partial": n_partial,
        "ring_missed": n_missed,
        "ring_recall_full": f"{n_full}/{n_rings}",
        "fp_legit_hv_fraud_only": hv_fraud_only,
        "fp_legit_hv_fraud_or_review": hv_fraud_or_review,
        "precision_fraud": round(precision_fraud, 4) if not np.isnan(precision_fraud) else "nan",
        "recall_fraud": round(recall_fraud, 4) if not np.isnan(recall_fraud) else "nan",
        "precision_at_10": round(p_at_10, 4) if not np.isnan(p_at_10) else "nan",
        "precision_at_50": round(p_at_50, 4) if not np.isnan(p_at_50) else "nan",
        "pr_auc": round(pr_auc, 4) if not np.isnan(pr_auc) else "nan",
        "elapsed_s": round(elapsed, 3),
        "latency_per_tx_ms": round(latency_per_tx_ms, 3),
        "degraded_stages": ",".join(result.degraded) if result.degraded else "none",
    }


def _approx_pr_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Approximate PR-AUC using trapezoidal integration."""
    if labels.sum() == 0:
        return float("nan")
    try:
        from sklearn.metrics import average_precision_score
        return float(average_precision_score(labels, scores))
    except Exception:
        return float("nan")
