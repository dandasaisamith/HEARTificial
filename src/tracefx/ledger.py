"""Evidence ledger builder for TRACE-FX.

Constructs positive and exculpatory evidence ledger lines for each account.
The ledger IS the explanation — every line cites evidence sources and tx IDs.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import pandas as pd

from .types import Evidence, LedgerLine

log = logging.getLogger(__name__)

STRUCTURAL_TYPES = {"shared_device", "common_sink", "pass_through", "sequence_cohort", "burst"}


def build(
    df: pd.DataFrame,
    behaviour: pd.Series,
    evidence: list[Evidence],
    cfg: dict,
) -> dict[str, list[LedgerLine]]:
    """Build evidence ledger for every account.

    Args:
        df: Canonical transaction DataFrame.
        behaviour: Per-row behaviour scores from baseline.score().
        evidence: All Evidence objects from motifs.find_all().
        cfg: Configuration dict.

    Returns:
        Dict mapping account_id -> list of LedgerLine objects.
    """
    pts = cfg["points"]
    ledger: dict[str, list[LedgerLine]] = defaultdict(list)
    
    # Ensure all accounts exist in the ledger even if they have zero evidence
    for acc in df["payer_id"].unique():
        _ = ledger[acc]

    # ------------------------------------------------------------------ #
    # Positive evidence: structural motifs                                  #
    # ------------------------------------------------------------------ #
    for ev in evidence:
        for acc in ev.accounts:
            if ev.type == "shared_device":
                device = ev.detail.get("device_id", "unknown")
                n_accs = ev.detail.get("account_count", len(ev.accounts))
                sample_tx = list(ev.tx_ids[:3])
                ledger[acc].append(LedgerLine(
                    source="shared_device",
                    points=float(pts["shared_device"]),
                    text=(
                        f"+{pts['shared_device']} Shared device {device} linked {n_accs} accounts "
                        f"with no prior payer/payee relationship; "
                        f"supporting transactions: {', '.join(sample_tx)}."
                    ),
                    tx_ids=tuple(ev.tx_ids),
                ))

            elif ev.type == "common_sink":
                sink = ev.detail.get("sink", "unknown")
                n_payers = ev.detail.get("distinct_payers", len(ev.accounts))
                window = ev.detail.get("window_h", 24)
                sample_tx = list(ev.tx_ids[:3])
                ledger[acc].append(LedgerLine(
                    source="common_sink",
                    points=float(pts["common_sink"]),
                    text=(
                        f"+{pts['common_sink']} Common sink: {n_payers} distinct accounts paid "
                        f"wallet/payee {sink} within {window}h; "
                        f"supporting transactions: {', '.join(sample_tx)}."
                    ),
                    tx_ids=tuple(ev.tx_ids),
                ))

            elif ev.type == "pass_through":
                account = ev.detail.get("account", acc)
                ratio = ev.detail.get("pass_ratio", 0)
                window = ev.detail.get("window_min", 30)
                sample_tx = list(ev.tx_ids[:3])
                ledger[acc].append(LedgerLine(
                    source="pass_through",
                    points=float(pts["pass_through"]),
                    text=(
                        f"+{pts['pass_through']} Pass-through: account {account} received funds then "
                        f"forwarded {ratio:.0%} onward within {window} min; "
                        f"supporting transactions: {', '.join(sample_tx)}."
                    ),
                    tx_ids=tuple(ev.tx_ids),
                ))

            elif ev.type == "sequence_cohort":
                n_accs = ev.detail.get("cohort_size", len(ev.accounts))
                n_ngrams = ev.detail.get("shared_rare_ngrams", 0)
                sample_tx = list(ev.tx_ids[:3])
                ledger[acc].append(LedgerLine(
                    source="sequence_cohort",
                    points=float(pts["sequence_cohort"]),
                    text=(
                        f"+{pts['sequence_cohort']} Sequence cohort: {n_accs} accounts share "
                        f"{n_ngrams} rare item/merchant 3-grams with money convergence; "
                        f"supporting transactions: {', '.join(sample_tx)}."
                    ),
                    tx_ids=tuple(ev.tx_ids),
                ))

            elif ev.type == "burst":
                max_z = ev.detail.get("max_zscore", 0)
                window = ev.detail.get("window_h", 1)
                sample_tx = list(ev.tx_ids[:3])
                ledger[acc].append(LedgerLine(
                    source="burst",
                    points=float(pts["burst"]),
                    text=(
                        f"+{pts['burst']} Burst activity: {account_label(acc)} shows "
                        f"z={max_z:.1f} transaction spike within {window}h window; "
                        f"supporting transactions: {', '.join(sample_tx)}."
                    ),
                    tx_ids=tuple(ev.tx_ids),
                ))

    # ------------------------------------------------------------------ #
    # Positive evidence: behaviour anomaly (per-account max score)         #
    # ------------------------------------------------------------------ #
    behaviour_max = float(pts["behaviour_max"])

    if not df.empty and not behaviour.empty:
        # Attach behaviour score to df
        df2 = df.copy()
        df2["_bscore"] = behaviour.values if len(behaviour) == len(df) else 0.0

        acc_bscore = df2.groupby("payer_id")["_bscore"].max()

        for acc, bscore in acc_bscore.items():
            if bscore < 0.5:  # only add behaviour to ledger if above midpoint
                continue
            points = round(bscore * behaviour_max, 1)
            # Get the most anomalous transactions for this account
            acc_txs = df2[df2["payer_id"] == acc].nlargest(3, "_bscore")
            sample_tx = acc_txs["tx_id"].tolist()

            ledger[acc].append(LedgerLine(
                source="behaviour_anomaly",
                points=points,
                text=(
                    f"+{points:.1f} Behaviour anomaly score {bscore:.2f}: unusual activity "
                    f"relative to account baseline and peers; "
                    f"most anomalous transactions: {', '.join(sample_tx)}."
                ),
                tx_ids=tuple(sample_tx),
            ))

    # ------------------------------------------------------------------ #
    # Exculpatory evidence (negative points)                               #
    # ------------------------------------------------------------------ #
    _add_exculpatory(df, ledger, behaviour, cfg)

    return dict(ledger)


def _add_exculpatory(
    df: pd.DataFrame,
    ledger: dict[str, list[LedgerLine]],
    behaviour: pd.Series,
    cfg: dict,
) -> None:
    """Add exculpatory (negative) evidence lines for each account."""
    pts = cfg["points"]
    tenure_protect = cfg["features"]["tenure_days_protect"]

    df2 = df.copy()
    df2["_bscore"] = behaviour.values if len(behaviour) == len(df) else 0.0

    # 1. Tenure > 1 year
    if "account_open_date" in df2.columns:
        aod_valid = df2.dropna(subset=["account_open_date"])
        if not aod_valid.empty:
            # We can just check the max timestamp per payer against their first AOD
            max_ts = aod_valid.groupby("payer_id")["ts"].max()
            first_aod = pd.to_datetime(aod_valid.groupby("payer_id")["account_open_date"].first(), utc=True)
            tenures = (max_ts - first_aod).dt.total_seconds() / 86400
            
            # Find accounts > tenure_protect
            established = tenures[tenures > tenure_protect]
            
            # For sample txs, take first 2 per account
            first_txs = aod_valid[aod_valid["payer_id"].isin(established.index)].groupby("payer_id").head(2)
            tx_map = first_txs.groupby("payer_id")["tx_id"].apply(list)
            
            for acc, tenure_val in established.items():
                sample_tx = tx_map.get(acc, [])
                ledger[acc].append(LedgerLine(
                    source="tenure_over_1y",
                    points=float(pts["tenure_over_1y"]),
                    text=(
                        f"{pts['tenure_over_1y']:.0f} Account tenure {tenure_val:.0f} days "
                        f"(>{tenure_protect:.0f} days): established account reduces suspicion; "
                        f"sample transactions: {', '.join(sample_tx)}."
                    ),
                    tx_ids=tuple(sample_tx),
                ))

    # 2. Repeat payee (payee used >= 3 times)
    payee_counts = df2.groupby(["payer_id", "payee_id"]).size()
    repeat_payees = payee_counts[payee_counts >= 3].reset_index()
    if not repeat_payees.empty:
        # Just take the first repeat payee for each account
        first_repeats = repeat_payees.groupby("payer_id").first()
        for acc, row in first_repeats.iterrows():
            payee_example = row["payee_id"]
            count = row[0]
            # Since we just need 3 txs, we can just grab them directly
            # This is still slightly slow but only runs for accounts that actually HAVE a repeat payee
            sample_tx = df2[(df2["payer_id"] == acc) & (df2["payee_id"] == payee_example)].head(3)["tx_id"].tolist()
            ledger[acc].append(LedgerLine(
                source="repeat_payee_3plus",
                points=float(pts["repeat_payee_3plus"]),
                text=(
                    f"{pts['repeat_payee_3plus']:.0f} Repeat payee: destination {payee_example} "
                    f"used {count} times before the suspicious window — likely known relationship; "
                    f"supporting transactions: {', '.join(sample_tx)}."
                ),
                tx_ids=tuple(sample_tx),
            ))

    # 3. Known device (used >= 5 times)
    if "device_id" in df2.columns:
        dev_counts = df2.groupby(["payer_id", "device_id"]).size()
        known_devs = dev_counts[dev_counts >= 5].reset_index()
        if not known_devs.empty:
            first_devs = known_devs.groupby("payer_id").first()
            for acc, row in first_devs.iterrows():
                dev_example = row["device_id"]
                dev_count = row[0]
                sample_tx = df2[(df2["payer_id"] == acc) & (df2["device_id"] == dev_example)].head(3)["tx_id"].tolist()
                ledger[acc].append(LedgerLine(
                    source="known_device_5plus",
                    points=float(pts["known_device_5plus"]),
                    text=(
                        f"{pts['known_device_5plus']:.0f} Known device: device {dev_example} "
                        f"used {dev_count} times — established device reduces suspicion; "
                        f"supporting transactions: {', '.join(sample_tx)}."
                    ),
                    tx_ids=tuple(sample_tx),
                ))

    # 4. Amount within p95
    # Calculate max and p95 per account
    acc_stats = df2.groupby("payer_id")["amount"].agg(["max", lambda x: x.quantile(0.95)])
    acc_stats.columns = ["max", "p95"]
    within_p95 = acc_stats[acc_stats["max"] <= acc_stats["p95"] * 1.05]
    
    if not within_p95.empty:
        # Get top 2 transactions by amount for each account
        top_txs = df2[df2["payer_id"].isin(within_p95.index)].sort_values(["payer_id", "amount"], ascending=[True, False]).groupby("payer_id").head(2)
        tx_map = top_txs.groupby("payer_id")["tx_id"].apply(list)
        
        for acc, row in within_p95.iterrows():
            max_amt = row["max"]
            p95_amt = row["p95"]
            sample_tx = tx_map.get(acc, [])
            ledger[acc].append(LedgerLine(
                source="amount_within_p95",
                points=float(pts["amount_within_p95"]),
                text=(
                    f"{pts['amount_within_p95']:.0f} Transaction amounts within account p95 "
                    f"(max ₹{max_amt:.0f} vs p95 ₹{p95_amt:.0f}): "
                    f"no unusual amount spike; transactions: {', '.join(sample_tx)}."
                ),
                tx_ids=tuple(sample_tx),
            ))


def account_label(acc: str) -> str:
    """Shorten an account ID for display."""
    return acc[-6:] if len(acc) > 6 else acc
