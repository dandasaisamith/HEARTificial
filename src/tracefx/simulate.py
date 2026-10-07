"""Deterministic transaction simulator for TRACE-FX.

Generates synthetic transaction data with realistic normal behaviour,
fraud rings R1/R2/R3, and all required hard negatives.

Ground truth is stored in truth_<seed>.json — NOT in the CSV.
The CSV never contains a 'label' column.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import string
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Data start time per spec
DATA_START = datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)

# Item catalogue
ITEM_CATALOGUE_FULL = [f"I{i:04d}" for i in range(300)]
ITEM_CATALOGUE_DEMO = [f"I{i:04d}" for i in range(150)]

# Merchant catalogue  
MERCHANT_CATALOGUE_FULL = [f"M{i:04d}" for i in range(120)]
MERCHANT_CATALOGUE_DEMO = [f"M{i:04d}" for i in range(60)]

CHANNELS = ["UPI", "CARD", "NETBANKING", "WALLET"]
CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
]


def generate(
    seed: int,
    n_accounts: int = 2000,
    n_days: int = 60,
    evasion: int = 0,
    is_demo: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Generate a synthetic transaction dataset with fraud scenarios.

    Args:
        seed: Random seed for determinism.
        n_accounts: Number of normal accounts (fraud accounts added on top).
        n_days: Number of days to simulate.
        evasion: Evasion level 0/1/2 for R1 ring.
        is_demo: If True, use smaller counts (demo_small config).

    Returns:
        Tuple of (transaction DataFrame, ground truth dict).
        DataFrame has NO 'label' column.
    """
    rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)

    item_cat = ITEM_CATALOGUE_DEMO if is_demo else ITEM_CATALOGUE_FULL
    merchant_cat = MERCHANT_CATALOGUE_DEMO if is_demo else MERCHANT_CATALOGUE_FULL

    # --------------- Account creation ---------------
    accounts = _generate_accounts(rng, n_accounts, seed, is_demo)

    # --------------- Normal transactions ---------------
    txns: list[dict] = []
    tx_counter = [0]

    def next_tx_id() -> str:
        tx_counter[0] += 1
        return f"T{tx_counter[0]:07d}"

    txns.extend(_generate_normal_transactions(
        accounts, n_days, rng, py_rng, item_cat, merchant_cat, next_tx_id, is_demo
    ))

    # --------------- Fraud rings ---------------
    truth: dict = {
        "seed": seed,
        "rings": [],
        "hard_negatives": [],
        "high_value_legit_tx_ids": [],
        "is_fraud_tx_ids": [],
        "demo_cases": {},
    }

    # R1: flagship ring
    r1_count_list = [10] if is_demo else [10, 7, 5]
    for idx, ring_size in enumerate(r1_count_list):
        ring_id = f"R1{'abc'[idx]}"
        ring_data = _generate_r1_ring(
            ring_id, ring_size, accounts, n_days, rng, py_rng,
            item_cat, next_tx_id, evasion,
        )
        txns.extend(ring_data["txns"])
        truth["rings"].append(ring_data["truth"])
        truth["is_fraud_tx_ids"].extend(ring_data["truth"]["cashout_tx_ids"])

    # R2: mule chain
    r2_count = 1 if is_demo else 2
    for idx in range(r2_count):
        ring_id = f"R2{'ab'[idx]}"
        ring_data = _generate_r2_chain(
            ring_id, accounts, n_days, rng, py_rng, next_tx_id,
        )
        txns.extend(ring_data["txns"])
        truth["rings"].append(ring_data["truth"])

    # R3: cyclic ring (seed C only — undetectable)
    # We generate it for all seeds but only plant the pattern in seed C condition
    if not is_demo and seed == 2026:
        ring_data = _generate_r3_cyclic(accounts, n_days, rng, py_rng, next_tx_id)
        txns.extend(ring_data["txns"])
        truth["rings"].append(ring_data["truth"])

    # --------------- Hard negatives ---------------
    hn_data = _generate_hard_negatives(
        accounts, n_days, rng, py_rng, item_cat, merchant_cat, next_tx_id, is_demo
    )
    txns.extend(hn_data["txns"])
    truth["hard_negatives"] = hn_data["hard_negatives"]
    truth["high_value_legit_tx_ids"] = hn_data["high_value_legit_tx_ids"]

    # Demo case mappings
    if is_demo and truth["rings"]:
        truth["demo_cases"]["A"] = truth["rings"][0]["id"]
        if hn_data["high_value_legit_tx_ids"]:
            truth["demo_cases"]["B"] = hn_data["high_value_legit_tx_ids"][0]
        if hn_data.get("family_large_tx"):
            truth["demo_cases"]["C"] = hn_data["family_large_tx"]
        if hn_data.get("traveller_tx"):
            truth["demo_cases"]["D"] = hn_data["traveller_tx"]

    # --------------- Assemble DataFrame ---------------
    df = pd.DataFrame(txns)

    # Ensure no label column
    if "label" in df.columns:
        df = df.drop(columns=["label"])

    # Sort by ts
    df["ts"] = pd.to_datetime(df["ts"], utc=True, format="mixed")
    df = df.sort_values("ts", kind="stable").reset_index(drop=True)

    # Ensure tx_id uniqueness
    df = df.drop_duplicates(subset=["tx_id"], keep="first").reset_index(drop=True)

    # Cast types
    df["amount"] = df["amount"].round(2)

    return df, truth


def _generate_accounts(
    rng: np.random.Generator,
    n: int,
    seed: int,
    is_demo: bool,
) -> list[dict]:
    """Generate account metadata with realistic tenure distribution."""
    accounts = []

    # Non-contiguous IDs — shuffle a range
    id_pool = list(range(10000, 99999))
    rng.shuffle(id_pool)
    account_ids = [f"A{id_pool[i]:05d}" for i in range(n)]

    # Tenure distribution: 70% >365d, 20% 90-365d, 10% <90d
    for i, acc_id in enumerate(account_ids):
        rand = rng.random()
        if rand < 0.70:
            tenure_days = int(rng.uniform(365, 1800))
        elif rand < 0.90:
            tenure_days = int(rng.uniform(90, 365))
        else:
            tenure_days = int(rng.uniform(1, 90))

        open_date = DATA_START - timedelta(days=tenure_days)

        # Amount profile: lognormal
        mu = float(rng.normal(math.log(800), 0.6))
        sigma = float(rng.uniform(0.3, 0.7))

        # City
        city = CITIES[i % len(CITIES)]
        home_ip = f"192.168.{i // 256 % 256}.{i % 256}"
        mobile_ip = f"10.{rng.integers(0, 254)}.{rng.integers(0, 254)}.{rng.integers(1, 254)}"

        # Devices
        n_devices = int(rng.integers(1, 3))
        devices = [f"D{rng.integers(10000, 99999)}" for _ in range(n_devices)]

        # Repeat payees: mix of personal and merchant
        n_payees = int(rng.integers(5, 16))

        accounts.append({
            "account_id": acc_id,
            "tenure_days": tenure_days,
            "account_open_date": open_date.date().isoformat(),
            "mu": mu,
            "sigma": sigma,
            "city": city,
            "home_ip": home_ip,
            "mobile_ip": mobile_ip,
            "devices": devices,
            "n_repeat_payees": n_payees,
        })

    return accounts


def _generate_normal_transactions(
    accounts: list[dict],
    n_days: int,
    rng: np.random.Generator,
    py_rng: random.Random,
    item_cat: list[str],
    merchant_cat: list[str],
    next_tx_id,
    is_demo: bool,
) -> list[dict]:
    """Generate realistic normal transaction behaviour."""
    txns = []
    tx_per_month = 8 if is_demo else 11
    tx_rate = tx_per_month / 30.0  # per day

    # Legit wallets (landlords, etc.)
    n_wallets = 15 if is_demo else 30
    wallets = [f"W{i:04d}" for i in range(n_wallets)]

    for acc in accounts:
        acc_id = acc["account_id"]
        # Poisson number of transactions
        n_txs = int(rng.poisson(tx_rate * n_days))
        if n_txs == 0:
            continue

        # Item preferences (Zipf)
        n_prefs = int(rng.integers(3, 7))
        item_prefs = py_rng.sample(item_cat[:50], min(n_prefs, len(item_cat[:50])))
        merchant_prefs = py_rng.sample(merchant_cat[:30], min(n_prefs, len(merchant_cat[:30])))

        # Generate timestamps spread across n_days
        day_offsets = sorted(rng.uniform(0, n_days * 86400, n_txs))

        for offset in day_offsets:
            ts = DATA_START + timedelta(seconds=float(offset))

            # Amount: lognormal, non-round
            amount = float(rng.lognormal(acc["mu"], acc["sigma"]))
            amount = max(10.0, min(50000.0, amount))
            # Make non-round: add small random cents
            if rng.random() < 0.9:  # 90% non-round
                amount = round(amount + rng.uniform(-0.99, 0.99), 2)
            else:
                amount = round(amount / 100) * 100.0

            # Device
            device = py_rng.choice(acc["devices"])

            # IP: 20% mobile
            ip = acc["mobile_ip"] if rng.random() < 0.20 else acc["home_ip"]

            # Channel
            channel = py_rng.choices(CHANNELS, weights=[50, 20, 15, 15])[0]

            # City: 95% home
            city = acc["city"] if rng.random() < 0.95 else py_rng.choice(CITIES)

            # Transaction type: 70% MERCHANT, 30% P2P
            if rng.random() < 0.70:
                tx_type = "MERCHANT"
                merchant_id = py_rng.choice(merchant_prefs) if merchant_prefs else py_rng.choice(merchant_cat)
                payee_id = merchant_id
                item_id = py_rng.choice(item_prefs) if item_prefs else py_rng.choice(item_cat)
            else:
                tx_type = "P2P"
                # Pay a known wallet or another account
                if rng.random() < 0.3 and wallets:
                    payee_id = py_rng.choice(wallets)
                else:
                    # Pay another account (not self)
                    payee_id = f"A{rng.integers(10000, 99999):05d}"
                merchant_id = None
                item_id = None

            txns.append({
                "tx_id": next_tx_id(),
                "ts": ts.isoformat(),
                "payer_id": acc_id,
                "payee_id": payee_id,
                "amount": amount,
                "tx_type": tx_type,
                "channel": channel,
                "device_id": device,
                "ip": ip,
                "merchant_id": merchant_id,
                "item_id": item_id,
                "city": city,
                "account_open_date": acc["account_open_date"],
            })

    return txns


def _generate_r1_ring(
    ring_id: str,
    ring_size: int,
    accounts: list[dict],
    n_days: int,
    rng: np.random.Generator,
    py_rng: random.Random,
    item_cat: list[str],
    next_tx_id,
    evasion: int = 0,
) -> dict:
    """Generate R1: flagship fraud ring with shared device, rare sequence, sink."""
    # Select ring accounts (non-contiguous subset)
    ring_accounts = py_rng.sample(accounts, ring_size)
    ring_ids = [acc["account_id"] for acc in ring_accounts]

    # Rare items: bottom-decile of catalogue
    rare_items = item_cat[:max(10, len(item_cat) // 10)]
    ring_sequence = py_rng.sample(rare_items, min(4, len(rare_items)))

    # Shared device (70-90% of members share it)
    shared_device = f"D{rng.integers(10000, 99999)}"
    device_fraction = rng.uniform(0.70, 0.90)
    device_users = py_rng.sample(ring_ids, max(2, int(ring_size * device_fraction)))

    # Sink wallet
    sink_wallet = f"W{rng.integers(9000, 9999)}"

    # External source wallet
    source_wallet = f"W{rng.integers(8000, 8999)}"

    # Ring start: 14 days of warm-up, then attack within 48h
    attack_start_day = int(rng.uniform(15, n_days - 3))
    attack_start = DATA_START + timedelta(days=attack_start_day)

    txns = []
    cashout_tx_ids = []
    tx_roles: dict[str, str] = {}

    # Warm-up: normal transactions for 14 days
    for acc in ring_accounts:
        n_warmup = int(rng.poisson(8.0))
        for j in range(n_warmup):
            offset = rng.uniform(0, attack_start_day * 86400 - 3600)
            ts = DATA_START + timedelta(seconds=float(offset))
            amount = float(rng.lognormal(acc["mu"], acc["sigma"]))
            amount = max(10.0, min(50000.0, round(amount + rng.uniform(-1, 1), 2)))
            tx_id = next_tx_id()
            dev = py_rng.choice(acc["devices"])
            txns.append({
                "tx_id": tx_id,
                "ts": ts.isoformat(),
                "payer_id": acc["account_id"],
                "payee_id": f"M{rng.integers(1000, 9999):04d}",
                "amount": amount,
                "tx_type": "MERCHANT",
                "channel": "UPI",
                "device_id": dev,
                "ip": acc["home_ip"],
                "merchant_id": f"M{rng.integers(1000, 9999):04d}",
                "item_id": py_rng.choice(item_cat[50:]),  # non-rare items
                "city": acc["city"],
                "account_open_date": acc["account_open_date"],
            })
            tx_roles[tx_id] = "warmup"

    # Attack phase
    for acc in ring_accounts:
        acc_id = acc["account_id"]
        dev = shared_device if acc_id in device_users else py_rng.choice(acc["devices"])

        # Apply evasion
        if evasion >= 1:
            dev = py_rng.choice(acc["devices"])  # no shared device

        # Inflow: receive 20k-60k from source wallet
        inflow_offset = rng.uniform(0, 3600)  # within first hour of attack
        if evasion >= 1:
            inflow_offset *= 3  # more jitter
        inflow_ts = attack_start + timedelta(seconds=float(inflow_offset))
        inflow_amount = float(rng.uniform(20000, 60000))
        inflow_tx = next_tx_id()
        txns.append({
            "tx_id": inflow_tx,
            "ts": inflow_ts.isoformat(),
            "payer_id": source_wallet,
            "payee_id": acc_id,
            "amount": round(inflow_amount, 2),
            "tx_type": "P2P",
            "channel": "WALLET",
            "device_id": dev,
            "ip": acc["home_ip"],
            "merchant_id": None,
            "item_id": None,
            "city": acc["city"],
            "account_open_date": acc["account_open_date"],
        })
        tx_roles[inflow_tx] = "inflow"

        # Sequence purchases using rare items
        n_seq_items = int(rng.integers(2, 5))
        seq_indices = sorted(py_rng.sample(range(len(ring_sequence)), min(n_seq_items, len(ring_sequence))))
        for k, seq_idx in enumerate(seq_indices):
            item = ring_sequence[seq_idx]
            # 30% chance of noise item inserted
            if py_rng.random() < 0.30:
                noise_item = py_rng.choice(item_cat[10:30])
                noise_ts = inflow_ts + timedelta(minutes=float(rng.uniform(1, 10)))
                noise_tx = next_tx_id()
                txns.append({
                    "tx_id": noise_tx,
                    "ts": noise_ts.isoformat(),
                    "payer_id": acc_id,
                    "payee_id": f"M{rng.integers(1000, 9999):04d}",
                    "amount": float(round(rng.uniform(100, 2000), 2)),
                    "tx_type": "MERCHANT",
                    "channel": "UPI",
                    "device_id": dev if evasion < 1 else py_rng.choice(acc["devices"]),
                    "ip": acc["home_ip"],
                    "merchant_id": f"M{rng.integers(1000, 9999):04d}",
                    "item_id": noise_item,
                    "city": acc["city"],
                    "account_open_date": acc["account_open_date"],
                })
                tx_roles[noise_tx] = "noise"

            seq_ts = inflow_ts + timedelta(minutes=float(k * 5 + rng.uniform(1, 10)))
            seq_tx = next_tx_id()
            txns.append({
                "tx_id": seq_tx,
                "ts": seq_ts.isoformat(),
                "payer_id": acc_id,
                "payee_id": f"M{rng.integers(1000, 9999):04d}",
                "amount": float(round(rng.uniform(500, 5000), 2)),
                "tx_type": "MERCHANT",
                "channel": "UPI",
                "device_id": dev if evasion < 1 else py_rng.choice(acc["devices"]),
                "ip": acc["home_ip"],
                "merchant_id": f"M{rng.integers(1000, 9999):04d}",
                "item_id": item,
                "city": acc["city"],
                "account_open_date": acc["account_open_date"],
            })
            tx_roles[seq_tx] = "purchase"

        # Cashout: 70% send 80-95% to sink within 5-30min; 30% within 30-90min
        if py_rng.random() < 0.70:
            cashout_delay = rng.uniform(5, 30)
        else:
            cashout_delay = rng.uniform(30, 90)

        if evasion >= 1:
            cashout_delay *= 3  # more jitter

        cashout_ts = inflow_ts + timedelta(minutes=float(cashout_delay))
        cashout_ratio = rng.uniform(0.80, 0.95)
        cashout_amount = round(inflow_amount * cashout_ratio, 2)

        # Evasion level 2: split sink across 3 wallets
        if evasion >= 2:
            sink_wallets = [sink_wallet, f"W{rng.integers(9000, 9999)}", f"W{rng.integers(9000, 9999)}"]
            split_amounts = [cashout_amount * 0.5, cashout_amount * 0.3, cashout_amount * 0.2]
            for sw, sa in zip(sink_wallets, split_amounts):
                co_tx = next_tx_id()
                txns.append({
                    "tx_id": co_tx,
                    "ts": cashout_ts.isoformat(),
                    "payer_id": acc_id,
                    "payee_id": sw,
                    "amount": round(sa, 2),
                    "tx_type": "P2P",
                    "channel": "WALLET",
                    "device_id": py_rng.choice(acc["devices"]),
                    "ip": acc["home_ip"],
                    "merchant_id": None,
                    "item_id": None,
                    "city": acc["city"],
                    "account_open_date": acc["account_open_date"],
                })
                cashout_tx_ids.append(co_tx)
                tx_roles[co_tx] = "outflow"
        else:
            co_tx = next_tx_id()
            txns.append({
                "tx_id": co_tx,
                "ts": cashout_ts.isoformat(),
                "payer_id": acc_id,
                "payee_id": sink_wallet,
                "amount": cashout_amount,
                "tx_type": "P2P",
                "channel": "WALLET",
                "device_id": dev if evasion < 1 else py_rng.choice(acc["devices"]),
                "ip": acc["home_ip"],
                "merchant_id": None,
                "item_id": None,
                "city": acc["city"],
                "account_open_date": acc["account_open_date"],
            })
            cashout_tx_ids.append(co_tx)
            tx_roles[co_tx] = "outflow"

    truth_entry = {
        "id": ring_id,
        "type": "R1",
        "accounts": ring_ids,
        "sink": sink_wallet,
        "devices": [shared_device] if evasion < 1 else [],
        "start_ts": attack_start.isoformat(),
        "cashout_tx_ids": cashout_tx_ids,
        "tx_roles": tx_roles,
    }

    return {"txns": txns, "truth": truth_entry}


def _generate_r2_chain(
    ring_id: str,
    accounts: list[dict],
    n_days: int,
    rng: np.random.Generator,
    py_rng: random.Random,
    next_tx_id,
) -> dict:
    """Generate R2: mule chain A->B->C->D->sink, no shared device/sequence."""
    chain_accounts = py_rng.sample(accounts, 4)
    chain_ids = [acc["account_id"] for acc in chain_accounts]
    sink = f"W{rng.integers(7000, 7999)}"

    start_day = int(rng.uniform(10, n_days - 2))
    start_ts = DATA_START + timedelta(days=start_day)

    txns = []
    tx_roles: dict[str, str] = {}
    pass_ratio = 0.85

    current_ts = start_ts
    current_amount = float(rng.uniform(50000, 150000))

    for hop_idx in range(len(chain_ids)):
        payer = chain_ids[hop_idx] if hop_idx > 0 else f"W{rng.integers(6000, 6999)}"
        payee = chain_ids[hop_idx] if hop_idx < len(chain_ids) else sink

        if hop_idx == 0:
            # Source -> first account
            tx_id = next_tx_id()
            txns.append({
                "tx_id": tx_id,
                "ts": current_ts.isoformat(),
                "payer_id": payer,
                "payee_id": chain_ids[0],
                "amount": round(current_amount, 2),
                "tx_type": "P2P",
                "channel": "WALLET",
                "device_id": py_rng.choice(chain_accounts[0]["devices"]),
                "ip": chain_accounts[0]["home_ip"],
                "merchant_id": None,
                "item_id": None,
                "city": chain_accounts[0]["city"],
                "account_open_date": chain_accounts[0]["account_open_date"],
            })
            tx_roles[tx_id] = "inflow"

        if hop_idx < len(chain_ids) - 1:
            # Forward to next account
            hop_delay = float(rng.uniform(5, 25))
            current_ts = current_ts + timedelta(minutes=hop_delay)
            hop_amount = round(current_amount * pass_ratio, 2)
            tx_id = next_tx_id()
            acc = chain_accounts[hop_idx]
            txns.append({
                "tx_id": tx_id,
                "ts": current_ts.isoformat(),
                "payer_id": chain_ids[hop_idx],
                "payee_id": chain_ids[hop_idx + 1],
                "amount": hop_amount,
                "tx_type": "P2P",
                "channel": "WALLET",
                "device_id": py_rng.choice(acc["devices"]),
                "ip": acc["home_ip"],
                "merchant_id": None,
                "item_id": None,
                "city": acc["city"],
                "account_open_date": acc["account_open_date"],
            })
            tx_roles[tx_id] = "chain_hop"
            current_amount = hop_amount
        else:
            # Last account -> sink
            hop_delay = float(rng.uniform(5, 25))
            current_ts = current_ts + timedelta(minutes=hop_delay)
            tx_id = next_tx_id()
            acc = chain_accounts[hop_idx]
            txns.append({
                "tx_id": tx_id,
                "ts": current_ts.isoformat(),
                "payer_id": chain_ids[hop_idx],
                "payee_id": sink,
                "amount": round(current_amount * pass_ratio, 2),
                "tx_type": "P2P",
                "channel": "WALLET",
                "device_id": py_rng.choice(acc["devices"]),
                "ip": acc["home_ip"],
                "merchant_id": None,
                "item_id": None,
                "city": acc["city"],
                "account_open_date": acc["account_open_date"],
            })
            tx_roles[tx_id] = "outflow"

    truth_entry = {
        "id": ring_id,
        "type": "R2",
        "accounts": chain_ids,
        "sink": sink,
        "devices": [],
        "start_ts": start_ts.isoformat(),
        "cashout_tx_ids": [tx_id],
        "tx_roles": tx_roles,
    }

    return {"txns": txns, "truth": truth_entry}


def _generate_r3_cyclic(
    accounts: list[dict],
    n_days: int,
    rng: np.random.Generator,
    py_rng: random.Random,
    next_tx_id,
) -> dict:
    """Generate R3: cyclic ring (undetectable — 4 accounts circulate money)."""
    ring_accounts = py_rng.sample(accounts, 4)
    ring_ids = [acc["account_id"] for acc in ring_accounts]

    start_day = int(rng.uniform(20, n_days - 1))
    start_ts = DATA_START + timedelta(days=start_day)

    txns = []
    tx_roles: dict[str, str] = {}
    amount = 30000.0

    # 3 cycles in 6 hours
    for cycle in range(3):
        for hop_idx in range(len(ring_ids)):
            payer_idx = hop_idx
            payee_idx = (hop_idx + 1) % len(ring_ids)
            offset_h = cycle * 2 + hop_idx * 0.4
            ts = start_ts + timedelta(hours=offset_h)
            tx_id = next_tx_id()
            acc = ring_accounts[payer_idx]
            txns.append({
                "tx_id": tx_id,
                "ts": ts.isoformat(),
                "payer_id": ring_ids[payer_idx],
                "payee_id": ring_ids[payee_idx],
                "amount": round(amount, 2),
                "tx_type": "P2P",
                "channel": "WALLET",
                "device_id": py_rng.choice(acc["devices"]),
                "ip": acc["home_ip"],
                "merchant_id": None,
                "item_id": None,
                "city": acc["city"],
                "account_open_date": acc["account_open_date"],
            })
            tx_roles[tx_id] = "cycle"

    truth_entry = {
        "id": "R3a",
        "type": "R3",
        "accounts": ring_ids,
        "sink": None,
        "devices": [],
        "start_ts": start_ts.isoformat(),
        "cashout_tx_ids": [],
        "tx_roles": tx_roles,
    }

    return {"txns": txns, "truth": truth_entry}


def _generate_hard_negatives(
    accounts: list[dict],
    n_days: int,
    rng: np.random.Generator,
    py_rng: random.Random,
    item_cat: list[str],
    merchant_cat: list[str],
    next_tx_id,
    is_demo: bool,
) -> dict:
    """Generate all required hard negatives."""
    txns = []
    hard_negatives = []
    high_value_legit_tx_ids = []
    family_large_tx = None
    traveller_tx = None

    n_family_groups = 2 if is_demo else 6
    n_hostel_accounts = 15 if is_demo else 30
    n_flash_accounts = 60 if is_demo else 200
    n_landlord_payers = 6 if is_demo else 12
    n_highvalue = 4 if is_demo else 15

    used_accounts = set()

    # 1. Family device groups (LEGIT or REVIEW, never FRAUD)
    family_hn_accounts = []
    for fg_idx in range(n_family_groups):
        family_size = int(rng.integers(2, 5))
        candidates = [a for a in accounts if a["account_id"] not in used_accounts and a["tenure_days"] > 365]
        if len(candidates) < family_size:
            continue
        family = py_rng.sample(candidates, family_size)
        family_ids = [a["account_id"] for a in family]
        family_hn_accounts.extend(family_ids)
        used_accounts.update(family_ids)

        shared_device = f"D{rng.integers(50000, 59999)}"
        shared_ip = f"192.168.10.{rng.integers(1, 50)}"

        # Prior payer/payee links between family members
        for i, acc in enumerate(family):
            other = family[(i + 1) % len(family)]
            link_ts = DATA_START + timedelta(days=int(rng.uniform(0, 5)))
            tx_id = next_tx_id()
            txns.append({
                "tx_id": tx_id,
                "ts": link_ts.isoformat(),
                "payer_id": acc["account_id"],
                "payee_id": other["account_id"],
                "amount": round(float(rng.uniform(500, 5000)), 2),
                "tx_type": "P2P",
                "channel": "UPI",
                "device_id": shared_device,
                "ip": shared_ip,
                "merchant_id": None,
                "item_id": None,
                "city": acc["city"],
                "account_open_date": acc["account_open_date"],
            })

        # One group has a large transfer (demo Case C)
        if fg_idx == 0:
            large_day = int(rng.uniform(20, n_days - 1))
            large_ts = DATA_START + timedelta(days=large_day)
            large_tx = next_tx_id()
            txns.append({
                "tx_id": large_tx,
                "ts": large_ts.isoformat(),
                "payer_id": family[0]["account_id"],
                "payee_id": family[1]["account_id"],
                "amount": round(float(rng.uniform(80000, 200000)), 2),
                "tx_type": "P2P",
                "channel": "NETBANKING",
                "device_id": shared_device,
                "ip": shared_ip,
                "merchant_id": None,
                "item_id": None,
                "city": family[0]["city"],
                "account_open_date": family[0]["account_open_date"],
            })
            family_large_tx = large_tx

        hard_negatives.append({
            "kind": "family_device",
            "accounts": family_ids,
            "tx_ids": [tx["tx_id"] for tx in txns[-family_size - 1:]],
        })

    # 2. Hostel/office IP (hub cap should eliminate evidence)
    hostel_candidates = [a for a in accounts if a["account_id"] not in used_accounts][:n_hostel_accounts]
    if len(hostel_candidates) >= 10:
        hostel_ids = [a["account_id"] for a in hostel_candidates]
        hostel_ip = f"172.16.{rng.integers(1, 50)}.1"
        hostel_txns = []
        for acc in hostel_candidates:
            for day in [1, 15, 25]:
                if day >= n_days:
                    continue
                ts = DATA_START + timedelta(days=day, hours=float(rng.uniform(8, 18)))
                tx_id = next_tx_id()
                hostel_txns.append(tx_id)
                txns.append({
                    "tx_id": tx_id,
                    "ts": ts.isoformat(),
                    "payer_id": acc["account_id"],
                    "payee_id": f"M{rng.integers(1000, 9999):04d}",
                    "amount": round(float(rng.uniform(100, 2000)), 2),
                    "tx_type": "MERCHANT",
                    "channel": "CARD",
                    "device_id": py_rng.choice(acc["devices"]),
                    "ip": hostel_ip,
                    "merchant_id": f"M{rng.integers(1000, 9999):04d}",
                    "item_id": py_rng.choice(item_cat),
                    "city": acc["city"],
                    "account_open_date": acc["account_open_date"],
                })

        hard_negatives.append({
            "kind": "hostel_ip",
            "accounts": hostel_ids,
            "tx_ids": hostel_txns[:20],
        })

    # 3. Flash-sale cohort (NO money convergence — M4 convergence rule must block)
    flash_candidates = [a for a in accounts
                        if a["account_id"] not in used_accounts and a["tenure_days"] > 180][:n_flash_accounts]
    if len(flash_candidates) >= 20:
        flash_ids = [a["account_id"] for a in flash_candidates]
        flash_sequence = py_rng.sample(item_cat[:50], 3)
        flash_merchant = py_rng.choice(merchant_cat)
        flash_day = int(rng.uniform(10, n_days - 1))
        flash_ts_base = DATA_START + timedelta(days=flash_day, hours=10)
        flash_txns = []

        for acc in flash_candidates:
            for seq_item in flash_sequence:
                offset = float(rng.uniform(0, 600))  # within 10 min
                ts = flash_ts_base + timedelta(seconds=offset)
                tx_id = next_tx_id()
                flash_txns.append(tx_id)
                txns.append({
                    "tx_id": tx_id,
                    "ts": ts.isoformat(),
                    "payer_id": acc["account_id"],
                    "payee_id": flash_merchant,
                    "amount": round(float(rng.uniform(500, 3000)), 2),
                    "tx_type": "MERCHANT",
                    "channel": "UPI",
                    "device_id": py_rng.choice(acc["devices"]),
                    "ip": acc["home_ip"],
                    "merchant_id": flash_merchant,
                    "item_id": seq_item,
                    "city": acc["city"],
                    "account_open_date": acc["account_open_date"],
                })

        hard_negatives.append({
            "kind": "flash_sale",
            "accounts": flash_ids,
            "tx_ids": flash_txns[:30],
        })

    # 4. Landlord wallet (many regular payers, monthly cadence — LEGIT)
    landlord_wallet = f"W{rng.integers(5000, 5999)}"
    landlord_candidates = [a for a in accounts
                           if a["account_id"] not in used_accounts and a["tenure_days"] > 365][:n_landlord_payers]
    if len(landlord_candidates) >= 4:
        landlord_ids = [a["account_id"] for a in landlord_candidates]
        landlord_txns = []
        for acc in landlord_candidates:
            for month_offset in [0, 30]:
                if month_offset >= n_days:
                    continue
                ts = DATA_START + timedelta(days=month_offset, hours=float(rng.uniform(9, 11)))
                tx_id = next_tx_id()
                landlord_txns.append(tx_id)
                txns.append({
                    "tx_id": tx_id,
                    "ts": ts.isoformat(),
                    "payer_id": acc["account_id"],
                    "payee_id": landlord_wallet,
                    "amount": round(float(rng.uniform(8000, 25000)), 2),
                    "tx_type": "P2P",
                    "channel": "NETBANKING",
                    "device_id": py_rng.choice(acc["devices"]),
                    "ip": acc["home_ip"],
                    "merchant_id": None,
                    "item_id": None,
                    "city": acc["city"],
                    "account_open_date": acc["account_open_date"],
                })

        hard_negatives.append({
            "kind": "landlord",
            "accounts": landlord_ids,
            "tx_ids": landlord_txns,
        })

    # 5. Salary-day burst (40% of accounts make bills on day 1 and 31 — no alert)
    salary_accounts = py_rng.sample(accounts, max(10, int(len(accounts) * 0.4)))
    salary_txns = []
    for day_offset in [0, 30]:
        if day_offset >= n_days:
            continue
        ts_base = DATA_START + timedelta(days=day_offset, hours=10)
        for acc in salary_accounts[:20]:
            ts = ts_base + timedelta(minutes=float(rng.uniform(0, 120)))
            tx_id = next_tx_id()
            salary_txns.append(tx_id)
            txns.append({
                "tx_id": tx_id,
                "ts": ts.isoformat(),
                "payer_id": acc["account_id"],
                "payee_id": f"W{rng.integers(1000, 2000)}_utility",
                "amount": round(float(rng.uniform(500, 5000)), 2),
                "tx_type": "P2P",
                "channel": "NETBANKING",
                "device_id": py_rng.choice(acc["devices"]),
                "ip": acc["home_ip"],
                "merchant_id": None,
                "item_id": None,
                "city": acc["city"],
                "account_open_date": acc["account_open_date"],
            })

    hard_negatives.append({
        "kind": "salary_burst",
        "accounts": [a["account_id"] for a in salary_accounts[:20]],
        "tx_ids": salary_txns[:20],
    })

    # 6. Traveller (new device + city, REVIEW or LEGIT, never FRAUD)
    n_travellers = 1 if is_demo else 3
    for trav_idx in range(n_travellers):
        trav_candidates = [a for a in accounts
                           if a["account_id"] not in used_accounts and a["tenure_days"] > 180]
        if not trav_candidates:
            continue
        trav = py_rng.choice(trav_candidates)
        new_city = py_rng.choice([c for c in CITIES if c != trav["city"]])
        new_device = f"D{rng.integers(70000, 79999)}"
        new_ip = f"10.{rng.integers(100, 200)}.{rng.integers(0, 255)}.{rng.integers(1, 254)}"

        trav_day = int(rng.uniform(10, n_days - 4))
        trav_txns = []
        for d in range(3):
            ts = DATA_START + timedelta(days=trav_day + d, hours=float(rng.uniform(9, 21)))
            tx_id = next_tx_id()
            trav_txns.append(tx_id)
            txns.append({
                "tx_id": tx_id,
                "ts": ts.isoformat(),
                "payer_id": trav["account_id"],
                "payee_id": f"M{rng.integers(1000, 9999):04d}",
                "amount": round(float(rng.uniform(500, 8000)), 2),
                "tx_type": "MERCHANT",
                "channel": "CARD",
                "device_id": new_device,
                "ip": new_ip,
                "merchant_id": f"M{rng.integers(1000, 9999):04d}",
                "item_id": py_rng.choice(item_cat),
                "city": new_city,
                "account_open_date": trav["account_open_date"],
            })

        if trav_idx == 0:
            traveller_tx = trav_txns[0] if trav_txns else None

        hard_negatives.append({
            "kind": "traveller",
            "accounts": [trav["account_id"]],
            "tx_ids": trav_txns,
        })

    # 7. High-value legit (old accounts, known payees — LEGIT with why-not panel)
    hv_candidates = [a for a in accounts
                     if a["account_id"] not in used_accounts and a["tenure_days"] > 730]
    hv_txns = []
    for hv in hv_candidates[:n_highvalue]:
        hv_day = int(rng.uniform(20, n_days - 1))
        ts = DATA_START + timedelta(days=hv_day, hours=float(rng.uniform(10, 16)))
        # Known repeat payee: merchant the account has used multiple times
        known_payee = f"M{rng.integers(1000, 9999):04d}"

        # First add some prior transactions to establish the payee as known
        for prior_day in [5, 15]:
            if prior_day >= n_days:
                continue
            prior_ts = DATA_START + timedelta(days=prior_day)
            prior_tx = next_tx_id()
            txns.append({
                "tx_id": prior_tx,
                "ts": prior_ts.isoformat(),
                "payer_id": hv["account_id"],
                "payee_id": known_payee,
                "amount": round(float(rng.uniform(5000, 20000)), 2),
                "tx_type": "MERCHANT",
                "channel": "CARD",
                "device_id": hv["devices"][0],
                "ip": hv["home_ip"],
                "merchant_id": known_payee,
                "item_id": py_rng.choice(item_cat),
                "city": hv["city"],
                "account_open_date": hv["account_open_date"],
            })

        tx_id = next_tx_id()
        hv_txns.append(tx_id)
        txns.append({
            "tx_id": tx_id,
            "ts": ts.isoformat(),
            "payer_id": hv["account_id"],
            "payee_id": known_payee,
            "amount": round(float(rng.uniform(80000, 400000)), 2),
            "tx_type": "MERCHANT",
            "channel": "NETBANKING",
            "device_id": hv["devices"][0],
            "ip": hv["home_ip"],
            "merchant_id": known_payee,
            "item_id": py_rng.choice(item_cat),
            "city": hv["city"],
            "account_open_date": hv["account_open_date"],
        })

    high_value_legit_tx_ids = hv_txns

    hard_negatives.append({
        "kind": "high_value_legit",
        "accounts": [a["account_id"] for a in hv_candidates[:n_highvalue]],
        "tx_ids": hv_txns,
    })

    return {
        "txns": txns,
        "hard_negatives": hard_negatives,
        "high_value_legit_tx_ids": high_value_legit_tx_ids,
        "family_large_tx": family_large_tx,
        "traveller_tx": traveller_tx,
    }


def generate_demo_small() -> tuple[pd.DataFrame, dict]:
    """Generate demo_small dataset (seed=42, 600 accounts, 30 days)."""
    return generate(seed=42, n_accounts=600, n_days=30, evasion=0, is_demo=True)


def dataset_hash(df: pd.DataFrame) -> str:
    """Compute a deterministic hash of a DataFrame for reproducibility testing."""
    content = df.to_csv(index=False).encode()
    return hashlib.sha256(content).hexdigest()[:16]


def save(
    df: pd.DataFrame,
    truth: dict,
    out_dir: str | Path,
    name: str,
) -> tuple[Path, Path]:
    """Save dataset CSV and truth JSON to out_dir."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"{name}.csv"
    truth_path = out_dir / f"truth_{name}.json"

    df.to_csv(csv_path, index=False)
    with open(truth_path, "w", encoding="utf-8") as f:
        json.dump(truth, f, indent=2, default=str)

    return csv_path, truth_path
