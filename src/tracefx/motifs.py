"""Fraud motif detectors M1–M5 for TRACE-FX.

Each motif returns a list of Evidence objects with:
- type: the motif name
- accounts: affected accounts
- tx_ids: supporting transaction IDs
- satisfied_at: causal timestamp (first moment evidence became true)
- strength: 0..1 signal strength

All detectors use ONLY past data relative to satisfied_at (causal).
Hub caps are applied in graph.py before calling motifs.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Optional

import networkx as nx
import numpy as np
import pandas as pd

from .types import Evidence

log = logging.getLogger(__name__)


def find_all(df: pd.DataFrame, G: nx.MultiGraph, cfg: dict) -> list[Evidence]:
    """Run all available motif detectors and return combined Evidence list.

    Args:
        df: Canonical transaction DataFrame (sorted by ts).
        G: Typed entity graph from graph.build().
        cfg: Configuration dict.

    Returns:
        List of Evidence objects from all fired motifs.
    """
    evidence: list[Evidence] = []

    def _run(name: str, fn, *args):
        try:
            result = fn(*args)
            if result:
                log.info("Motif %s: %d evidence items", name, len(result))
            evidence.extend(result)
        except Exception as exc:
            log.warning("Motif %s failed: %s", name, exc, exc_info=True)

    _run("M1", _m1_shared_device, df, G, cfg)
    _run("M2", _m2_common_sink, df, cfg)
    _run("M3", _m3_pass_through, df, cfg)
    _run("M4", _m4_sequence_cohort, df, cfg, evidence)
    _run("M5", _m5_burst, df, cfg)

    return evidence


# ---------------------------------------------------------------------------
# M1 — Shared Device
# ---------------------------------------------------------------------------

def _m1_shared_device(df: pd.DataFrame, G: nx.MultiGraph, cfg: dict) -> list[Evidence]:
    """Detect accounts sharing a device with no prior payer/payee relationship.

    Hub caps have already been applied in graph.py — we only see devices
    connected to <= deg_cap_device accounts.
    """
    evidence = []

    # Get device -> accounts from graph (hub-capped already)
    device_accounts: dict[str, list[str]] = defaultdict(list)
    for u, v, data in G.edges(data=True):
        if data.get("edge_type") == "uses_device":
            dev = data.get("device_id") or (v if G.nodes.get(v, {}).get("node_type") == "device" else u)
            acc = u if G.nodes.get(u, {}).get("node_type") == "account" else v
            device_accounts[dev].append(acc)

    # Build static pairs for O(1) prior link checks
    pairs = set(zip(df["payer_id"], df["payee_id"]))

    for device, accounts in device_accounts.items():
        accounts = list(set(accounts))
        if len(accounts) < 2:
            continue

        # Check for prior payer/payee links between account pairs
        no_prior_pairs: list[tuple[str, str]] = []
        all_accounts_set = set(accounts)

        for i, a in enumerate(accounts):
            for b in accounts[i+1:]:
                if not ((a, b) in pairs or (b, a) in pairs):
                    no_prior_pairs.append((a, b))

        if not no_prior_pairs:
            continue  # All pairs have prior links — likely family/business

        # Gather supporting transactions for this device
        if "device_id" not in df.columns:
            continue

        device_txs = df[df["device_id"] == device].copy()
        if device_txs.empty:
            continue

        # Include only accounts with no-prior pairs
        no_prior_accounts = set()
        for a, b in no_prior_pairs:
            no_prior_accounts.add(a)
            no_prior_accounts.add(b)

        device_txs = device_txs[device_txs["payer_id"].isin(no_prior_accounts)]
        if device_txs.empty:
            continue

        # Causal: satisfied_at = earliest tx where >=2 distinct accounts used this device
        txs_sorted = device_txs.sort_values("ts")
        seen_accounts: set = set()
        satisfied_at = None
        satisfied_tx_ids = []

        for payer, tx_id, ts in zip(txs_sorted["payer_id"], txs_sorted["tx_id"], txs_sorted["ts"]):
            seen_accounts.add(payer)
            satisfied_tx_ids.append(tx_id)
            if len(seen_accounts & no_prior_accounts) >= 2:
                satisfied_at = str(ts)
                break

        if satisfied_at is None:
            continue

        # Strength based on number of accounts sharing (capped)
        strength = min(1.0, (len(no_prior_accounts) - 1) / 5.0)

        evidence.append(Evidence(
            type="shared_device",
            accounts=tuple(sorted(no_prior_accounts)),
            tx_ids=tuple(device_txs["tx_id"].tolist()),
            first_ts=str(device_txs["ts"].min()),
            last_ts=str(device_txs["ts"].max()),
            satisfied_at=satisfied_at,
            strength=strength,
            detail={
                "device_id": device,
                "account_count": len(no_prior_accounts),
                "no_prior_pairs": len(no_prior_pairs),
            },
        ))

    return evidence


def _prior_link(df: pd.DataFrame, a: str, b: str) -> bool:
    pass # Obsolete


# ---------------------------------------------------------------------------
# M2 — Common Sink
# ---------------------------------------------------------------------------

def _m2_common_sink(df: pd.DataFrame, cfg: dict) -> list[Evidence]:
    """Detect payees receiving from >= min_payers distinct accounts within window_h."""
    min_payers = cfg["motifs"]["common_sink"]["min_payers"]
    window_h = cfg["motifs"]["common_sink"]["window_h"]
    window_ns = int(window_h * 3600 * 1e9)

    evidence = []

    # Sort by ts
    df_sorted = df.sort_values("ts")
    ts_ns = pd.to_datetime(df_sorted["ts"], utc=True).dt.tz_localize(None).astype("datetime64[ns]").astype("int64").values
    payee_arr = df_sorted["payee_id"].values
    payer_arr = df_sorted["payer_id"].values
    txid_arr = df_sorted["tx_id"].values

    # Build payee -> list of (ts_ns, payer, tx_id)
    payee_events: dict[str, list[tuple]] = defaultdict(list)
    for i in range(len(df_sorted)):
        payee_events[payee_arr[i]].append((ts_ns[i], payer_arr[i], txid_arr[i]))

    seen_sinks: set[str] = set()

    for payee, events in payee_events.items():
        events.sort(key=lambda x: x[0])

        # Sliding window: find first window where >= min_payers distinct payers appear
        for start_idx in range(len(events)):
            t_start = events[start_idx][0]
            t_end = t_start + window_ns

            window_events = [e for e in events if t_start <= e[0] <= t_end]
            distinct_payers = set(e[1] for e in window_events)

            if len(distinct_payers) >= min_payers:
                # Check cadence: is this a legitimate recurring payee?
                # If the payee has been receiving from SAME payers regularly, discount
                if _is_cadenced_legitimate(events, distinct_payers):
                    break  # legitimate recurring payment destination

                # Causal: satisfied_at = ts of the (min_payers)-th distinct payer
                payers_seen: set = set()
                satisfied_at = None
                satisfied_tx_ids = []
                for t, payer, tx_id in events:
                    payers_seen.add(payer)
                    satisfied_tx_ids.append(tx_id)
                    if len(payers_seen) >= min_payers:
                        satisfied_at = str(
                            pd.Timestamp(t, unit="ns", tz="UTC")
                        )
                        break

                if satisfied_at is None or payee in seen_sinks:
                    break

                seen_sinks.add(payee)
                all_accounts = set(e[1] for e in window_events) | {payee}
                strength = min(1.0, (len(distinct_payers) - min_payers + 1) / 6.0)

                evidence.append(Evidence(
                    type="common_sink",
                    accounts=tuple(sorted(all_accounts)),
                    tx_ids=tuple(e[2] for e in window_events),
                    first_ts=str(pd.Timestamp(events[start_idx][0], unit="ns", tz="UTC")),
                    last_ts=str(pd.Timestamp(window_events[-1][0], unit="ns", tz="UTC")),
                    satisfied_at=satisfied_at,
                    strength=strength,
                    detail={
                        "sink": payee,
                        "distinct_payers": len(distinct_payers),
                        "window_h": window_h,
                    },
                ))
                break

    return evidence


def _is_cadenced_legitimate(
    events: list[tuple],
    distinct_payers: set,
    cadence_days: float = 25.0,
    min_cadence_count: int = 2,
) -> bool:
    """Check if a payee appears to be a legitimate recurring destination.

    A payee is considered legitimate if the same payers have paid it
    repeatedly with a roughly monthly cadence.
    """
    # Group by payer, check if each has multiple events with ~monthly gap
    payer_times: dict[str, list[int]] = defaultdict(list)
    for t, payer, _ in events:
        payer_times[payer].append(t)

    cadenced_payers = 0
    cadence_ns = int(cadence_days * 86400 * 1e9)

    for payer, times in payer_times.items():
        if payer not in distinct_payers:
            continue
        times.sort()
        if len(times) >= min_cadence_count:
            # Check if any consecutive pair is ~monthly apart
            for i in range(len(times) - 1):
                gap = times[i+1] - times[i]
                if gap >= cadence_ns * 0.7:  # within 70% of monthly
                    cadenced_payers += 1
                    break

    # If most distinct payers have cadenced payments, this is likely legitimate
    return cadenced_payers >= len(distinct_payers) * 0.6 and cadenced_payers >= min_cadence_count


# ---------------------------------------------------------------------------
# M3 — Pass-Through
# ---------------------------------------------------------------------------

def _m3_pass_through(df: pd.DataFrame, cfg: dict) -> list[Evidence]:
    """Detect accounts receiving money then passing >= 80% onward within 30min."""
    min_ratio = cfg["motifs"]["pass_through"]["min_ratio"]
    window_min = cfg["motifs"]["pass_through"]["window_min"]
    window_ns = int(window_min * 60 * 1e9)

    evidence = []

    df_sorted = df.sort_values("ts").reset_index(drop=True)
    ts_ns = pd.to_datetime(df_sorted["ts"], utc=True).dt.tz_localize(None).astype("datetime64[ns]").astype("int64").values

    # Build indexed lookups
    # For each account: list of (ts_ns, tx_id, amount, direction)
    # direction: 'in' (payee), 'out' (payer)
    account_flows: dict[str, list[tuple]] = defaultdict(list)
    for ts_val, payee, payer, tx_id, amt in zip(ts_ns, df_sorted["payee_id"], df_sorted["payer_id"], df_sorted["tx_id"], df_sorted["amount"]):
        account_flows[payee].append(
            (ts_val, tx_id, float(amt), "in")
        )
        account_flows[payer].append(
            (ts_val, tx_id, float(amt), "out")
        )

    seen_chains: set[frozenset] = set()

    for account, flows in account_flows.items():
        flows.sort(key=lambda x: x[0])

        inflows = [(t, txid, amt) for t, txid, amt, d in flows if d == "in"]
        outflows = [(t, txid, amt) for t, txid, amt, d in flows if d == "out"]

        if not inflows or not outflows:
            continue

        for in_t, in_txid, in_amt in inflows:
            # Find outflows within the window AFTER this inflow
            window_out = [
                (t, txid, amt) for t, txid, amt in outflows
                if in_t < t <= in_t + window_ns
            ]
            if not window_out:
                continue

            total_out = sum(amt for _, _, amt in window_out)
            ratio = total_out / max(in_amt, 1e-6)

            if ratio >= min_ratio:
                # Causal: satisfied at the last qualifying outflow
                satisfied_at = str(
                    pd.Timestamp(window_out[-1][0], unit="ns", tz="UTC")
                )
                all_tx = [in_txid] + [tx for _, tx, _ in window_out]
                chain_key = frozenset(all_tx)

                if chain_key in seen_chains:
                    continue
                seen_chains.add(chain_key)

                # Get payee of outflows (onward destinations)
                out_payees = set()
                for _, out_txid, _ in window_out:
                    out_rows = df_sorted[df_sorted["tx_id"] == out_txid]
                    if not out_rows.empty:
                        out_payees.add(out_rows.iloc[0]["payee_id"])

                accounts_involved = {account} | out_payees
                # Source payer(s)
                in_rows = df_sorted[df_sorted["tx_id"] == in_txid]
                if not in_rows.empty:
                    accounts_involved.add(in_rows.iloc[0]["payer_id"])

                # Strength: higher ratio = stronger, multi-hop chains get bonus
                chain_length = len(out_payees)
                strength = min(1.0, ratio * 0.7 + (chain_length - 1) * 0.1)

                evidence.append(Evidence(
                    type="pass_through",
                    accounts=tuple(sorted(accounts_involved)),
                    tx_ids=tuple(all_tx),
                    first_ts=str(pd.Timestamp(in_t, unit="ns", tz="UTC")),
                    last_ts=satisfied_at,
                    satisfied_at=satisfied_at,
                    strength=strength,
                    detail={
                        "account": account,
                        "pass_ratio": round(ratio, 3),
                        "inflow_amount": round(in_amt, 2),
                        "outflow_amount": round(total_out, 2),
                        "window_min": window_min,
                    },
                ))

    return evidence


# ---------------------------------------------------------------------------
# M4 — Sequence Cohort (with convergence rule)
# ---------------------------------------------------------------------------

def _m4_sequence_cohort(
    df: pd.DataFrame,
    cfg: dict,
    existing_evidence: list[Evidence],
) -> list[Evidence]:
    """Detect accounts sharing rare item/merchant sequences.

    CRITICAL: Sequence cohort evidence only counts when the cohort also shows
    money convergence (M2 common_sink or M3 pass_through evidence).
    This prevents flash-sale crowds from being falsely classified.
    """
    seq_cfg = cfg["motifs"]["sequence"]
    ngram_size = seq_cfg["ngram"]
    min_shared_rare = seq_cfg["min_shared_rare"]
    min_cohort = seq_cfg["min_cohort"]
    rare_quantile = seq_cfg["idf_rare_quantile"]
    require_convergence = seq_cfg.get("require_convergence", True)

    # Need item or merchant tokens
    token_col = None
    if "item_id" in df.columns and df["item_id"].notna().any():
        token_col = "item_id"
    elif "merchant_id" in df.columns and df["merchant_id"].notna().any():
        token_col = "merchant_id"

    if token_col is None:
        return []

    df_tok = df[df[token_col].notna()].copy()
    if df_tok.empty:
        return []

    # Build per-account ordered token sequences
    account_seqs: dict[str, list[str]] = {}
    for acc, grp in df_tok.sort_values("ts").groupby("payer_id"):
        tokens = grp[token_col].tolist()
        if len(tokens) >= ngram_size:
            account_seqs[acc] = tokens

    if not account_seqs:
        return []

    # Build ngrams per account
    def get_ngrams(tokens: list[str], n: int) -> list[tuple]:
        return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]

    # IDF: count how many accounts use each ngram
    ngram_account_count: dict[tuple, int] = defaultdict(int)
    account_ngrams: dict[str, list[tuple]] = {}

    for acc, tokens in account_seqs.items():
        ngrams = list(set(get_ngrams(tokens, ngram_size)))
        account_ngrams[acc] = ngrams
        for ng in ngrams:
            ngram_account_count[ng] += 1

    n_accounts = len(account_seqs)
    if n_accounts == 0:
        return []

    # Compute IDF: log(N / df(ng))
    ngram_idf = {
        ng: math.log(n_accounts / max(cnt, 1))
        for ng, cnt in ngram_account_count.items()
    }

    # Rare ngrams: those above the rare_quantile threshold of IDF
    idf_values = list(ngram_idf.values())
    if not idf_values:
        return []
    idf_threshold = np.quantile(idf_values, rare_quantile)
    rare_ngrams = {ng for ng, idf in ngram_idf.items() if idf >= idf_threshold}

    # Build inverted index: rare_ngram -> accounts that have it
    ngram_to_accounts: dict[tuple, set] = defaultdict(set)
    for acc, ngrams in account_ngrams.items():
        for ng in ngrams:
            if ng in rare_ngrams:
                ngram_to_accounts[ng].add(acc)

    # Find cohorts: accounts sharing >= min_shared_rare rare ngrams
    # Use a union-find style approach via inverted index
    account_rare_ngrams: dict[str, set] = defaultdict(set)
    for ng, accounts in ngram_to_accounts.items():
        if len(accounts) >= 2:  # shared by at least 2
            for acc in accounts:
                account_rare_ngrams[acc].add(ng)

    # Find cohort candidates: pairs sharing multiple rare ngrams
    shared_ngrams: dict[frozenset, set] = defaultdict(set)
    for ng, accounts in ngram_to_accounts.items():
        accs = list(accounts)
        for i in range(len(accs)):
            for j in range(i+1, len(accs)):
                pair = frozenset([accs[i], accs[j]])
                shared_ngrams[pair].add(ng)

    # Build cohorts from pairs sharing >= min_shared_rare ngrams
    strong_pairs = {
        pair: ngs
        for pair, ngs in shared_ngrams.items()
        if len(ngs) >= min_shared_rare
    }

    if not strong_pairs:
        return []

    # Union-find to group into cohorts
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for pair in strong_pairs:
        a, b = list(pair)
        union(a, b)

    # Group accounts by component
    groups: dict[str, set] = defaultdict(set)
    for acc in set(a for pair in strong_pairs for a in pair):
        groups[find(acc)].add(acc)

    evidence = []

    # Check for convergence in existing evidence (M2/M3)
    convergence_accounts: set[str] = set()
    for ev in existing_evidence:
        if ev.type in ("common_sink", "pass_through"):
            convergence_accounts.update(ev.accounts)

    for root, cohort_accounts in groups.items():
        if len(cohort_accounts) < min_cohort:
            continue

        # Gather shared ngrams for this cohort
        cohort_ngrams: set[tuple] = set()
        for pair, ngs in strong_pairs.items():
            a, b = list(pair)
            if a in cohort_accounts and b in cohort_accounts:
                cohort_ngrams.update(ngs)

        # Get supporting transactions
        cohort_txs = df_tok[df_tok["payer_id"].isin(cohort_accounts)]

        if cohort_txs.empty:
            continue

        # Check convergence requirement
        if require_convergence:
            overlap = cohort_accounts & convergence_accounts
            if len(overlap) < 2:
                # No money convergence — flash-sale cohort, not fraud
                log.debug(
                    "M4 cohort of %d accounts has no convergence — skipping (flash-sale guard)",
                    len(cohort_accounts),
                )
                continue

        # Causal: satisfied_at = ts when min_cohort accounts first shared a rare ngram
        # Approximate by the time all cohort members had made enough transactions
        txs_sorted = cohort_txs.sort_values("ts")
        seen_cohort_accs: set = set()
        satisfied_at = None

        for payer, ts in zip(txs_sorted["payer_id"], txs_sorted["ts"]):
            seen_cohort_accs.add(payer)
            if len(seen_cohort_accs) >= min_cohort:
                satisfied_at = str(ts)
                break

        if satisfied_at is None:
            continue

        # Strength: based on cohort size and shared ngram count
        strength = min(1.0, len(cohort_accounts) / 10.0 + len(cohort_ngrams) / 20.0)

        evidence.append(Evidence(
            type="sequence_cohort",
            accounts=tuple(sorted(cohort_accounts)),
            tx_ids=tuple(cohort_txs["tx_id"].tolist()),
            first_ts=str(cohort_txs["ts"].min()),
            last_ts=str(cohort_txs["ts"].max()),
            satisfied_at=satisfied_at,
            strength=strength,
            detail={
                "shared_rare_ngrams": len(cohort_ngrams),
                "ngram_size": ngram_size,
                "cohort_size": len(cohort_accounts),
                "sample_ngrams": [str(ng) for ng in list(cohort_ngrams)[:3]],
            },
        ))

    return evidence


# ---------------------------------------------------------------------------
# M5 — Burst
# ---------------------------------------------------------------------------

def _m5_burst(df: pd.DataFrame, cfg: dict) -> list[Evidence]:
    """Detect unusual short-window activity relative to account baseline.

    Threshold: z > burst.z within a window_h window.
    """
    z_threshold = cfg["motifs"]["burst"]["z"]
    window_h = cfg["motifs"]["burst"]["window_h"]
    window_ns = int(window_h * 3600 * 1e9)

    evidence = []

    df_sorted = df.sort_values("ts").reset_index(drop=True)
    ts_ns = pd.to_datetime(df_sorted["ts"], utc=True).dt.tz_localize(None).astype("datetime64[ns]").astype("int64").values
    payer_arr = df_sorted["payer_id"].values
    txid_arr = df_sorted["tx_id"].values

    # Build per-account time series of transaction counts
    from collections import defaultdict
    payer_events: dict[str, list[tuple]] = defaultdict(list)
    for i in range(len(df_sorted)):
        payer_events[payer_arr[i]].append((ts_ns[i], txid_arr[i]))

    seen_accounts: set[str] = set()

    for account, events in payer_events.items():
        if len(events) < 5:  # need enough history to establish baseline
            continue

        events.sort(key=lambda x: x[0])
        times = np.array([e[0] for e in events])

        # Calculate rolling 1h counts for each event (past only)
        counts = []
        for i, t in enumerate(times):
            past = times[:i]
            cnt = np.sum(past > t - window_ns)
            counts.append(cnt)

        counts = np.array(counts, dtype=float)
        if len(counts) < 5:
            continue

        mean_count = counts.mean()
        std_count = counts.std()
        if std_count < 1e-6:
            continue

        # Find windows where z > threshold
        zscores = (counts - mean_count) / std_count
        burst_mask = zscores > z_threshold

        if not burst_mask.any():
            continue

        burst_indices = np.where(burst_mask)[0]
        first_burst_idx = burst_indices[0]
        satisfied_at = str(pd.Timestamp(times[first_burst_idx], unit="ns", tz="UTC"))

        burst_tx_ids = [events[i][1] for i in burst_indices[:10]]  # cap tx list

        if account in seen_accounts:
            continue
        seen_accounts.add(account)

        strength = min(1.0, float(zscores[burst_indices].max()) / 10.0)

        evidence.append(Evidence(
            type="burst",
            accounts=(account,),
            tx_ids=tuple(burst_tx_ids),
            first_ts=str(pd.Timestamp(times[first_burst_idx], unit="ns", tz="UTC")),
            last_ts=str(pd.Timestamp(times[burst_indices[-1]], unit="ns", tz="UTC")),
            satisfied_at=satisfied_at,
            strength=strength,
            detail={
                "account": account,
                "max_zscore": round(float(zscores.max()), 2),
                "burst_count": int(burst_mask.sum()),
                "window_h": window_h,
            },
        ))

    return evidence
