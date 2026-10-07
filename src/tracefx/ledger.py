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

    # Per-account stats
    for acc, grp in df2.groupby("payer_id"):
        acc_lines = ledger[acc]  # may be empty if no positive evidence yet
        # Still add exculpatory — it will be visible in the why-not panel

        # 1. Tenure > 1 year
        if "account_open_date" in grp.columns:
            aod = grp["account_open_date"].dropna()
            if not aod.empty:
                tenure = (grp["ts"].max() - pd.to_datetime(aod.iloc[0], utc=True)).total_seconds() / 86400
                if tenure > tenure_protect:
                    sample_tx = grp.sort_values("ts").head(2)["tx_id"].tolist()
                    ledger[acc].append(LedgerLine(
                        source="tenure_over_1y",
                        points=float(pts["tenure_over_1y"]),
                        text=(
                            f"{pts['tenure_over_1y']:.0f} Account tenure {tenure:.0f} days "
                            f"(>{tenure_protect:.0f} days): established account reduces suspicion; "
                            f"sample transactions: {', '.join(sample_tx)}."
                        ),
                        tx_ids=tuple(sample_tx),
                    ))

        # 2. Repeat payee (payee used >= 3 times)
        payee_counts = grp["payee_id"].value_counts()
        repeat_payees = payee_counts[payee_counts >= 3]
        if not repeat_payees.empty:
            payee_example = repeat_payees.index[0]
            count = int(repeat_payees.iloc[0])
            sample_tx = grp[grp["payee_id"] == payee_example].head(3)["tx_id"].tolist()
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
        if "device_id" in grp.columns:
            dev_counts = grp["device_id"].dropna().value_counts()
            known_devs = dev_counts[dev_counts >= 5]
            if not known_devs.empty:
                dev_example = known_devs.index[0]
                dev_count = int(known_devs.iloc[0])
                sample_tx = grp[grp["device_id"] == dev_example].head(3)["tx_id"].tolist()
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
        amounts = grp["amount"]
        p95 = amounts.quantile(0.95)
        if amounts.max() <= p95 * 1.05:  # within 5% of p95
            sample_tx = grp.nlargest(2, "amount")["tx_id"].tolist()
            ledger[acc].append(LedgerLine(
                source="amount_within_p95",
                points=float(pts["amount_within_p95"]),
                text=(
                    f"{pts['amount_within_p95']:.0f} Transaction amounts within account p95 "
                    f"(max ₹{amounts.max():.0f} vs p95 ₹{p95:.0f}): "
                    f"no unusual amount spike; transactions: {', '.join(sample_tx)}."
                ),
                tx_ids=tuple(sample_tx),
            ))


def account_label(acc: str) -> str:
    """Shorten an account ID for display."""
    return acc[-6:] if len(acc) > 6 else acc
