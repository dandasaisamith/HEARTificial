import streamlit as st
import json
import pandas as pd
from tracefx.evaluate import _approx_pr_auc
from ui import datasets

st.title("DETECTION QUALITY")
st.markdown("How reliably does TRACE-FX find, rank and control fraud decisions?")

if "run_result" not in st.session_state or st.session_state.run_result is None:
    st.warning("Run TRACE-FX before reviewing detection quality.")
    st.stop()
    
res = st.session_state.run_result
ds_info = st.session_state.get("selected_dataset")

if not ds_info:
    st.warning("No dataset selected.")
    st.stop()

meta = datasets.load_dataset_metadata(ds_info["path"])

if not meta.get("has_truth"):
    st.error("GROUND TRUTH NOT AVAILABLE FOR THIS DATASET")
    st.markdown("Classification metrics require labelled truth data.")
    st.markdown("### Verifiable Pipeline Stages:")
    st.markdown("- ✅ Behavioural Scoring (Isolation Forest)")
    st.markdown("- ✅ Structural Evidence (M1-M5 Motifs)")
    st.markdown("- ✅ Evidence Ledger Accumulation")
    st.markdown("- ✅ Precision Gate Math")
    st.markdown("- ✅ Suspicious Ring Discovery")
    st.markdown("- ✅ Deterministic Explanations")
    st.markdown("---")
    st.info("To view strict evaluation metrics (Precision, Recall, PR-AUC), select a labelled dataset like `demo_small.csv` or `seedA.csv` in Mission Control.")
    st.stop()

# Load truth
with open(meta["truth_path"], "r") as f:
    truth = json.load(f)

# Re-implement metric calc for the *existing* result
accs = res.accounts.set_index("account_id") if not res.accounts.empty else pd.DataFrame()
rings = truth.get("rings", [])
n_rings = len(rings)
n_full, n_partial, n_missed = 0, 0, 0

for ring in rings:
    ring_accounts = set(ring.get("accounts", []))
    if not ring_accounts: continue
    
    best_overlap = 0
    for group in res.groups:
        group_accs = set(group.accounts)
        overlap = len(ring_accounts & group_accs) / len(ring_accounts)
        best_overlap = max(best_overlap, overlap)
        
    if best_overlap >= 0.8: n_full += 1
    elif best_overlap >= 0.4: n_partial += 1
    else: n_missed += 1

hv_tx_ids = set(truth.get("high_value_legit_tx_ids", []))
hv_fraud_only = 0
hv_fraud_or_review = 0

if hv_tx_ids and not res.tx.empty:
    hv_txs = res.tx[res.tx["tx_id"].isin(hv_tx_ids)]
    if not hv_txs.empty:
        hv_fraud_only = int((hv_txs["tx_label"] == "FRAUD").sum())
        hv_fraud_or_review = int(hv_txs["tx_label"].isin(["FRAUD", "REVIEW"]).sum())

fraud_tx_ids = set(truth.get("is_fraud_tx_ids", []))
ring_accounts = set()
for ring in rings:
    if ring.get("type") == "R1":
        ring_accounts.update(ring.get("accounts", []))

tp_fraud, precision_fraud, recall_fraud = 0, float("nan"), float("nan")
p_at_10, p_at_50, pr_auc = float("nan"), float("nan"), float("nan")

if not accs.empty and ring_accounts:
    pred_fraud_accs = set(accs[accs["label"] == "FRAUD"].index)
    tp_fraud = len(pred_fraud_accs & ring_accounts)
    precision_fraud = tp_fraud / max(len(pred_fraud_accs), 1)
    recall_fraud = tp_fraud / max(len(ring_accounts), 1)
    
    top10 = accs.nlargest(10, "risk").index.tolist()
    p_at_10 = len(set(top10) & ring_accounts) / max(len(top10), 1)
    
    top50 = accs.nlargest(50, "risk").index.tolist()
    p_at_50 = len(set(top50) & ring_accounts) / max(len(top50), 1)
    
    all_risks = accs["risk"].values
    all_labels = accs.index.map(lambda x: 1 if x in ring_accounts else 0).values
    pr_auc = _approx_pr_auc(all_risks, all_labels)

# Additive metrics: anyring
anyring_accounts = set()
for ring in rings:
    anyring_accounts.update(ring.get("accounts", []))
fraud_payers = set()
if fraud_tx_ids and not res.tx.empty:
    fraud_payers = set(res.tx[res.tx["tx_id"].isin(fraud_tx_ids)]["payer_id"])
hard_negatives = truth.get("hard_negatives", [])
hard_negative_accs = set()
for hn in hard_negatives:
    hard_negative_accs.update(hn.get("accounts", []))
anyring_positives = (anyring_accounts | fraud_payers) - hard_negative_accs

precision_fraud_any, recall_fraud_any = float("nan"), float("nan")
precision_for_any, recall_for_any = float("nan"), float("nan")

if not accs.empty and anyring_positives:
    pred_fraud = set(accs[accs["label"] == "FRAUD"].index)
    pred_review = set(accs[accs["label"] == "REVIEW"].index)
    pred_fraud_or_review = pred_fraud | pred_review

    tp_fraud_any = len(pred_fraud & anyring_positives)
    precision_fraud_any = tp_fraud_any / max(len(pred_fraud), 1)
    recall_fraud_any = tp_fraud_any / max(len(anyring_positives), 1)

    tp_for_any = len(pred_fraud_or_review & anyring_positives)
    precision_for_any = tp_for_any / max(len(pred_fraud_or_review), 1)
    recall_for_any = tp_for_any / max(len(anyring_positives), 1)

st.markdown("### Strict Detection Metrics (FRAUD vs R1)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Precision", f"{precision_fraud:.2%}" if not pd.isna(precision_fraud) else "N/A", help="Strict FRAUD predictions that match pure R1 fraud.")
c2.metric("Recall", f"{recall_fraud:.2%}" if not pd.isna(recall_fraud) else "N/A", help="Strict R1 fraud detected as FRAUD.")
c3.metric("PR-AUC", f"{pr_auc:.3f}" if not pd.isna(pr_auc) else "N/A", help="Area under Precision-Recall curve.")
c4.metric("Ring Recall", f"{n_full}/{n_rings}", help="Fraud rings structurally recovered.")

st.markdown("### Any-Ring Detection Metrics (All Motifs)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Any-Ring Precision (FRAUD)", f"{precision_fraud_any:.2%}" if not pd.isna(precision_fraud_any) else "N/A")
c2.metric("Any-Ring Recall (FRAUD)", f"{recall_fraud_any:.2%}" if not pd.isna(recall_fraud_any) else "N/A")
c3.metric("Any-Ring Precision (FRAUD/REVIEW)", f"{precision_for_any:.2%}" if not pd.isna(precision_for_any) else "N/A")
c4.metric("Any-Ring Recall (FRAUD/REVIEW)", f"{recall_for_any:.2%}" if not pd.isna(recall_for_any) else "N/A")

st.markdown("### Ranking Quality")
c1, c2 = st.columns(2)
c1.metric("Precision @ 10", f"{p_at_10:.2%}" if not pd.isna(p_at_10) else "N/A", help="Fraud concentration in top 10 riskiest.")
c2.metric("Precision @ 50", f"{p_at_50:.2%}" if not pd.isna(p_at_50) else "N/A", help="Fraud concentration in top 50 riskiest.")

st.markdown("### False Positive Control (PS04 Requirement)")
c1, c2 = st.columns(2)
c1.metric("Legit High-Value called FRAUD", hv_fraud_only, help="High-value legit transactions blocked. Should be 0.")
c2.metric("Legit High-Value called FRAUD/REVIEW", hv_fraud_or_review, help="High-value legit transactions reviewed.")
