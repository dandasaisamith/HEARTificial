"""Behaviour scoring for TRACE-FX.

Uses IsolationForest by default to score how anomalous each transaction is
relative to the overall distribution. Score is in [0, 1].

Critical constraint: behaviour score alone NEVER produces FRAUD.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

log = logging.getLogger(__name__)

# Feature columns used for anomaly scoring (must not include future info)
_SCORE_COLS = [
    "amount_zscore",
    "hour_zscore",
    "velocity_1h",
    "velocity_24h",
    "new_payee_flag",
    "new_device_flag",
    "amount_vs_p95",
    "amount_pct_rank",
]


def score(feat: pd.DataFrame, cfg: dict) -> pd.Series:
    """Score each transaction's behavioural anomaly using IsolationForest.

    Args:
        feat: Feature DataFrame from features.build().
        cfg: Configuration dict.

    Returns:
        pd.Series of behaviour scores in [0, 1] aligned with feat index.
        0 = completely normal, 1 = maximally anomalous.
    """
    contamination = cfg["baseline"]["contamination"]
    seed = cfg.get("seed", 42)

    # Select available feature columns
    use_cols = [c for c in _SCORE_COLS if c in feat.columns]
    if not use_cols:
        log.warning("No feature columns available for scoring; returning neutral 0.0")
        return pd.Series(0.0, index=feat.index)

    X = feat[use_cols].fillna(0.0).values.astype(float)

    # Robust scaling to reduce influence of extreme outliers on the forest
    scaler = RobustScaler()
    X_scaled = scaler.fit_transform(X)

    # IsolationForest: higher contamination = more anomalies
    iso = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=seed,
        n_jobs=1,
    )
    iso.fit(X_scaled)

    # decision_function: negative scores = more anomalous
    raw = iso.decision_function(X_scaled)

    # Normalize to [0, 1]: 0 = normal, 1 = anomalous
    # Map: most negative -> 1, most positive -> 0
    rmin, rmax = raw.min(), raw.max()
    if rmax - rmin < 1e-9:
        normalized = np.zeros(len(raw))
    else:
        normalized = 1.0 - (raw - rmin) / (rmax - rmin)

    return pd.Series(normalized.astype(float), index=feat.index, name="behaviour_score")
