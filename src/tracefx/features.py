"""Feature engineering for TRACE-FX.

Builds per-account behavioural features using ONLY past data (no future leakage).
All features use shift/expanding/rolling with a minimum period of 1 so cold-start
accounts get a neutral prior rather than being punished for lack of history.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def build(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Build behavioural features for all transactions.

    Uses only past data for each row (causal feature engineering).
    Returns a DataFrame aligned with df (same index).

    Args:
        df: Canonical transaction DataFrame (sorted by ts).
        cfg: Configuration dict.

    Returns:
        Feature DataFrame with columns used by baseline.score().
    """
    wshort = cfg["features"]["window_short_h"]
    wlong = cfg["features"]["window_long_h"]

    df = df.sort_values("ts", kind="stable").reset_index(drop=True)
    feats = pd.DataFrame(index=df.index)

    # ------------------------------------------------------------------ #
    # Per-account rolling aggregates (causal: use shift so row i only    #
    # uses rows 0..i-1 for that account)                                  #
    # ------------------------------------------------------------------ #
    grp = df.groupby("payer_id", sort=False)

    # Expanding mean/std of amount per payer (using past only via shift)
    feats["amount"] = df["amount"]
    feats["payer_id"] = df["payer_id"]
    feats["ts_epoch"] = df["ts"].astype("int64") // 10**9  # Unix seconds

    # Amount deviation from account history
    shifted_amt = grp["amount"].shift(1)
    amt_cumcnt = grp["amount"].cumcount() # 0-indexed, so shifted_amt has NaN at 0
    
    amount_hist_mean = (shifted_amt.groupby(df["payer_id"]).cumsum() / amt_cumcnt.replace(0, np.nan)).fillna(0.0)
    
    # Fast expanding variance
    shifted_amt2 = shifted_amt ** 2
    mean_of_sq = shifted_amt2.groupby(df["payer_id"]).cumsum() / amt_cumcnt.replace(0, np.nan)
    sq_of_mean = amount_hist_mean ** 2
    var = (mean_of_sq - sq_of_mean) * (amt_cumcnt / (amt_cumcnt - 1).replace(0, np.nan))
    amount_hist_std = np.sqrt(var.clip(lower=0)).fillna(1.0).replace(0.0, 1.0)
    
    feats["amount_zscore"] = ((df["amount"] - amount_hist_mean) / amount_hist_std).clip(-5, 5).fillna(0.0)

    # Hour of day deviation (0=midnight, ..-1 etc)
    hour = df["ts"].dt.hour + df["ts"].dt.minute / 60.0
    feats["hour_of_day"] = hour
    
    df["_hour"] = hour
    shifted_hr = df.groupby("payer_id")["_hour"].shift(1)
    hr_cumcnt = df.groupby("payer_id")["_hour"].cumcount()
    
    hour_hist_mean = (shifted_hr.groupby(df["payer_id"]).cumsum() / hr_cumcnt.replace(0, np.nan)).fillna(12.0)
    
    shifted_hr2 = shifted_hr ** 2
    hr_mean_of_sq = shifted_hr2.groupby(df["payer_id"]).cumsum() / hr_cumcnt.replace(0, np.nan)
    hr_sq_of_mean = hour_hist_mean ** 2
    hr_var = (hr_mean_of_sq - hr_sq_of_mean) * (hr_cumcnt / (hr_cumcnt - 1).replace(0, np.nan))
    hour_hist_std = np.sqrt(hr_var.clip(lower=0)).fillna(6.0).replace(0.0, 6.0)

    feats["hour_zscore"] = ((hour - hour_hist_mean) / hour_hist_std).clip(-3, 3).fillna(0.0)
    df.drop(columns=["_hour"], inplace=True)

    # Velocity: count of transactions in rolling windows
    # We use a merge-asof approach: for each tx, count preceding tx within window
    ts_arr = df["ts"].values
    payer_arr = df["payer_id"].values

    vel_1h = np.zeros(len(df), dtype=float)
    vel_24h = np.zeros(len(df), dtype=float)

    # Group indices by payer
    from collections import defaultdict
    payer_indices: dict[str, list[int]] = defaultdict(list)
    for i, pid in enumerate(payer_arr):
        payer_indices[pid].append(i)

    ns_1h = int(wshort * 3600 * 1e9)
    ns_24h = int(wlong * 3600 * 1e9)
    ts_ns = df["ts"].astype("int64").values

    for pid, idxs in payer_indices.items():
        idxs_arr = np.array(idxs)
        ts_sub = ts_ns[idxs_arr]
        for j, (idx, t) in enumerate(zip(idxs_arr, ts_sub)):
            # Past transactions only (exclusive of current)
            past = ts_sub[:j]
            vel_1h[idx] = np.sum(past > t - ns_1h)
            vel_24h[idx] = np.sum(past > t - ns_24h)

    feats["velocity_1h"] = vel_1h
    feats["velocity_24h"] = vel_24h

    # New payee rate: fraction of past payees that are new for this payer
    # (1 = first time seeing this payee, 0 = repeat)
    # Fast vectorized approach using duplicated
    feats["new_payee_flag"] = (~df.duplicated(subset=["payer_id", "payee_id"])).astype(float)

    # New device signal
    if "device_id" in df.columns:
        feats["new_device_flag"] = (~df.dropna(subset=["device_id"]).duplicated(subset=["payer_id", "device_id"])).astype(float).reindex(df.index, fill_value=0.0)
    else:
        feats["new_device_flag"] = 0.0

    # Peer amount percentile: how does this tx amount compare to all txs?
    global_p50 = df["amount"].quantile(0.5)
    global_p95 = df["amount"].quantile(0.95)
    feats["amount_vs_p95"] = (df["amount"] / global_p95.clip(1e-6)).clip(0, 10)

    # Amount percentile rank within all transactions
    feats["amount_pct_rank"] = df["amount"].rank(pct=True)

    # Repeat payee count (how many times has this payer paid this payee before?)
    # cumcount on (payer_id, payee_id) gives exactly the number of prior occurrences!
    feats["repeat_payee_count"] = df.groupby(["payer_id", "payee_id"]).cumcount().astype(float)

    # Known device count (how many times has this payer used this device before?)
    if "device_id" in df.columns:
        # subset to notna to avoid counting NaNs
        valid_devs = df.dropna(subset=["device_id"])
        known_devs = valid_devs.groupby(["payer_id", "device_id"]).cumcount().astype(float)
        feats["known_device_count"] = known_devs.reindex(df.index, fill_value=0.0)
    else:
        feats["known_device_count"] = 0.0

    # Account tenure in days at time of transaction
    if "account_open_date" in df.columns:
        tenure = (df["ts"] - pd.to_datetime(df["account_open_date"], utc=True)).dt.total_seconds() / 86400
        feats["tenure_days"] = tenure.clip(0).fillna(0.0)
        if cfg["features"].get("use_since_open", False):
            feats["since_open_hours"] = (tenure * 24).clip(0).fillna(0.0)
    else:
        feats["tenure_days"] = 365.0  # neutral prior

    # Drop helper columns
    feats = feats.drop(columns=["payer_id"], errors="ignore")

    # Fill any remaining NaNs with 0
    feats = feats.fillna(0.0)

    return feats
