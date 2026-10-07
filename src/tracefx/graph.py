"""Typed entity graph construction for TRACE-FX.

Builds a NetworkX MultiGraph with hub-capped edges representing
evidence-relevant relationships between accounts, devices, IPs, etc.

Critical: hub caps prevent shared infrastructure (hostel Wi-Fi, office IP)
from creating false fraud rings.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import networkx as nx
import pandas as pd

log = logging.getLogger(__name__)


def build(df: pd.DataFrame, cfg: dict) -> nx.MultiGraph:
    """Build the typed entity graph from transaction data.

    Nodes represent: accounts (payer_id/payee_id), devices, IPs.
    Edges represent: payment relationships, device usage, IP usage.

    Hub caps are applied: devices/IPs with too many accounts are treated
    as shared public infrastructure and not added as evidence links.

    Args:
        df: Canonical transaction DataFrame.
        cfg: Configuration dict.

    Returns:
        NetworkX MultiGraph with typed edges.
    """
    cap_device = cfg["graph"]["deg_cap_device"]
    cap_ip = cfg["graph"]["deg_cap_ip"]

    G = nx.MultiGraph()

    # Index: device -> set of payer accounts
    device_accounts: dict[str, set] = defaultdict(set)
    ip_accounts: dict[str, set] = defaultdict(set)

    if "device_id" in df.columns:
        for _, row in df[df["device_id"].notna()].iterrows():
            device_accounts[row["device_id"]].add(row["payer_id"])

    if "ip" in df.columns:
        for _, row in df[df["ip"].notna()].iterrows():
            ip_accounts[row["ip"]].add(row["payer_id"])

    # Add payer->payee payment edges
    for _, row in df.iterrows():
        payer = row["payer_id"]
        payee = row["payee_id"]

        if not G.has_node(payer):
            G.add_node(payer, node_type="account")
        if not G.has_node(payee):
            G.add_node(payee, node_type="account")

        G.add_edge(
            payer,
            payee,
            edge_type="payment",
            tx_id=row["tx_id"],
            amount=float(row["amount"]),
            ts=str(row["ts"]),
        )

    # Add device edges (hub-capped)
    if "device_id" in df.columns:
        for device, accounts in device_accounts.items():
            accs = list(accounts)
            if len(accs) > cap_device:
                # Shared/public infrastructure — no evidence links
                log.debug(
                    "Device %s has %d accounts (>%d cap): treating as shared infrastructure",
                    device,
                    len(accs),
                    cap_device,
                )
                continue

            if not G.has_node(device):
                G.add_node(device, node_type="device")

            for acc in accs:
                G.add_edge(acc, device, edge_type="uses_device", device_id=device)

    # Add IP edges (hub-capped)
    if "ip" in df.columns:
        for ip, accounts in ip_accounts.items():
            accs = list(accounts)
            if len(accs) > cap_ip:
                # Shared/public infrastructure — no evidence links
                log.debug(
                    "IP %s has %d accounts (>%d cap): treating as shared infrastructure",
                    ip,
                    len(accs),
                    cap_ip,
                )
                continue

            if not G.has_node(ip):
                G.add_node(ip, node_type="ip")

            for acc in accs:
                G.add_edge(acc, ip, edge_type="uses_ip", ip=ip)

    log.info(
        "Graph built: %d nodes, %d edges",
        G.number_of_nodes(),
        G.number_of_edges(),
    )
    return G


def get_device_accounts(G: nx.MultiGraph) -> dict[str, list[str]]:
    """Return dict of device_id -> [account_ids] from graph."""
    result: dict[str, list[str]] = defaultdict(list)
    for u, v, data in G.edges(data=True):
        if data.get("edge_type") == "uses_device":
            device = data.get("device_id") or v
            account = u if G.nodes[u].get("node_type") == "account" else v
            result[device].append(account)
    return dict(result)


def get_payment_graph(G: nx.MultiGraph) -> nx.DiGraph:
    """Extract directed payment edges as a DiGraph for pass-through analysis."""
    DG = nx.DiGraph()
    for u, v, data in G.edges(data=True):
        if data.get("edge_type") == "payment":
            if DG.has_edge(u, v):
                DG[u][v]["tx_ids"].append(data["tx_id"])
                DG[u][v]["total_amount"] += data["amount"]
            else:
                DG.add_edge(
                    u,
                    v,
                    tx_ids=[data["tx_id"]],
                    total_amount=data["amount"],
                    ts=data["ts"],
                )
    return DG


def prior_payer_payee_link(df: pd.DataFrame, acc_a: str, acc_b: str) -> bool:
    """Check if there is a prior payer/payee relationship between two accounts."""
    mask = (
        ((df["payer_id"] == acc_a) & (df["payee_id"] == acc_b))
        | ((df["payer_id"] == acc_b) & (df["payee_id"] == acc_a))
    )
    return bool(mask.any())
