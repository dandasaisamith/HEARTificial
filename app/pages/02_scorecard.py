import streamlit as st
import json
import pandas as pd
from tracefx.evaluate import _approx_pr_auc

st.title("Accuracy Scorecard")
st.markdown("Honest performance metrics computed directly from pipeline outputs.")

if "run_result" not in st.session_state or st.session_state.run_result is None:
    st.warning("Please run a dataset in Mission Control first.")
    st.stop()
    
res = st.session_state.run_result
ds_info = st.session_state.get("selected_dataset")

if not ds_info:
    st.warning("No dataset selected.")
    st.stop()

from ui import datasets
meta = datasets.load_dataset_metadata(ds_info["path"])

if not meta.get("has_truth"):
    st.info("Evaluation metrics require labeled truth data. This dataset has no ground truth.")
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

# Precision
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

# UI Layout
st.markdown("### Decision Metrics")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Precision (Strict)", f"{precision_fraud:.2%}" if not pd.isna(precision_fraud) else "N/A", help="When TRACE-FX says FRAUD, % that is actually fraud.")
c2.metric("Recall (Strict)", f"{recall_fraud:.2%}" if not pd.isna(recall_fraud) else "N/A", help="Fraction of known fraud captured by strict FRAUD decisions.")
c3.metric("PR-AUC", f"{pr_auc:.3f}" if not pd.isna(pr_auc) else "N/A", help="Overall ranking quality under class imbalance.")
c4.metric("Ring Recall", f"{n_full}/{n_rings}", help="Fraud rings fully identified.")

st.markdown("### Ranking")
c1, c2 = st.columns(2)
c1.metric("Precision @ 10", f"{p_at_10:.2%}" if not pd.isna(p_at_10) else "N/A", help="How many of the top 10 ranked cases are fraud.")
c2.metric("Precision @ 50", f"{p_at_50:.2%}" if not pd.isna(p_at_50) else "N/A", help="How many of the top 50 ranked cases are fraud.")

st.markdown("### False Positive Protection")
c1, c2 = st.columns(2)
c1.metric("Legit High-Value called FRAUD", hv_fraud_only, help="Strict FRAUD false positives on legitimate high value transactions.")
c2.metric("Legit High-Value called FRAUD/REVIEW", hv_fraud_or_review)

st.markdown("---")
st.markdown("*(Any-ring / softer metrics available in full evaluation report)*")
