"""Schema loading, validation, and capability detection for TRACE-FX.

Maps incoming column names to canonical names, deduplicates on tx_id,
parses timestamps to UTC, produces a quality report, and identifies
which optional motifs are available given the columns present.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

# Canonical required columns
REQUIRED_COLS = {"tx_id", "ts", "payer_id", "payee_id", "amount"}

# Canonical optional columns
OPTIONAL_COLS = {
    "tx_type", "device_id", "ip", "merchant_id", "item_id",
    "channel", "city", "account_open_date", "label",
}

# Default column name aliases (lowercase key -> canonical name)
_DEFAULT_ALIASES: dict[str, str] = {
    "transaction_id": "tx_id",
    "txn_id": "tx_id",
    "id": "tx_id",
    "timestamp": "ts",
    "datetime": "ts",
    "time": "ts",
    "sender": "payer_id",
    "sender_id": "payer_id",
    "source": "payer_id",
    "receiver": "payee_id",
    "receiver_id": "payee_id",
    "dest": "payee_id",
    "destination": "payee_id",
    "value": "amount",
    "sum": "amount",
    "device": "device_id",
    "ip_address": "ip",
    "merchant": "merchant_id",
    "item": "item_id",
}


def load(
    path: str | Path,
    mapping: Optional[dict[str, str]] = None,
) -> pd.DataFrame:
    """Load a transaction CSV into canonical schema.

    Args:
        path: Path to CSV file.
        mapping: Optional dict of {input_col: canonical_col} overrides.

    Returns:
        DataFrame with canonical columns, timestamps in UTC, tx_id deduplicated.

    Raises:
        ValueError: If required columns are missing after mapping.
        FileNotFoundError: If path does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Transaction file not found: {path}")

    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    # Build column mapping: user-supplied overrides, then default aliases
    col_map = dict(_DEFAULT_ALIASES)
    if mapping:
        col_map.update({k.lower(): v for k, v in mapping.items()})

    # Apply mapping
    rename = {}
    for col in df.columns:
        canonical = col_map.get(col.lower())
        if canonical and col not in (REQUIRED_COLS | OPTIONAL_COLS):
            rename[col] = canonical
    if rename:
        df = df.rename(columns=rename)

    # Check required columns
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}. "
            f"Available: {sorted(df.columns.tolist())}. "
            "Use the 'mapping' parameter to map input column names."
        )

    # Parse and normalize amount
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    if df["amount"].isna().any():
        n_bad = df["amount"].isna().sum()
        log.warning("Dropping %d rows with unparseable 'amount'", n_bad)
        df = df.dropna(subset=["amount"]).copy()

    # Parse timestamps to UTC
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce", format="mixed")
    n_bad_ts = df["ts"].isna().sum()
    if n_bad_ts > 0:
        log.warning("Dropping %d rows with unparseable 'ts'", n_bad_ts)
        df = df.dropna(subset=["ts"]).copy()

    # Deduplicate on tx_id (keep first)
    n_before = len(df)
    df = df.drop_duplicates(subset=["tx_id"], keep="first").copy()
    n_dupes = n_before - len(df)
    if n_dupes > 0:
        log.warning("Dropped %d duplicate tx_id rows", n_dupes)

    # Parse account_open_date if present
    if "account_open_date" in df.columns:
        df["account_open_date"] = pd.to_datetime(df["account_open_date"], errors="coerce")

    # Sort by timestamp
    df = df.sort_values("ts", kind="stable").reset_index(drop=True)

    log.info("Loaded %d transactions from %s", len(df), path.name)
    return df


def quality_report(df: pd.DataFrame) -> dict:
    """Generate a data quality report for a loaded transaction DataFrame.

    Returns:
        Dict with quality metrics and capability flags.
    """
    total = len(df)
    report: dict = {
        "total_rows": total,
        "unique_tx_ids": int(df["tx_id"].nunique()),
        "date_range": {
            "min": str(df["ts"].min()),
            "max": str(df["ts"].max()),
        },
        "unique_payers": int(df["payer_id"].nunique()),
        "unique_payees": int(df["payee_id"].nunique()),
        "amount_stats": {
            "min": float(df["amount"].min()),
            "max": float(df["amount"].max()),
            "mean": float(df["amount"].mean()),
            "p50": float(df["amount"].quantile(0.5)),
            "p95": float(df["amount"].quantile(0.95)),
            "p99": float(df["amount"].quantile(0.99)),
        },
        "missing": {},
        "capabilities": capabilities(df),
    }

    for col in list(REQUIRED_COLS) + list(OPTIONAL_COLS):
        if col in df.columns:
            n_miss = int(df[col].isna().sum())
            if n_miss:
                report["missing"][col] = n_miss

    if "tx_type" in df.columns:
        report["tx_type_dist"] = df["tx_type"].value_counts().to_dict()

    return report


def capabilities(df: pd.DataFrame) -> dict:
    """Detect which motifs/features are available given column presence.

    Returns:
        Dict of capability flags used to populate Result.capabilities.
    """
    cols = set(df.columns)
    has_device = "device_id" in cols and df["device_id"].notna().any()
    has_ip = "ip" in cols and df["ip"].notna().any()
    has_item = "item_id" in cols and df["item_id"].notna().any()
    has_merchant = "merchant_id" in cols and df["merchant_id"].notna().any()
    has_city = "city" in cols and df["city"].notna().any()
    has_aod = "account_open_date" in cols and df["account_open_date"].notna().any()

    return {
        "device_evidence": has_device,
        "ip_evidence": has_ip,
        "sequence_evidence": has_item or has_merchant,
        "merchant_evidence": has_merchant,
        "city_evidence": has_city,
        "tenure_evidence": has_aod,
        # Motif availability
        "M1_shared_device": has_device,
        "M2_common_sink": True,   # only needs payer/payee/amount/ts
        "M3_pass_through": True,
        "M4_sequence_cohort": has_item or has_merchant,
        "M5_burst": True,
    }
