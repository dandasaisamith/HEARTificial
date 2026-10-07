import streamlit as st
import pandas as pd
import time
from tracefx import schema, engine_api
from ui import datasets

st.title("TRACE-FX")
st.markdown("### Temporal Risk & Coordinated Evidence Engine")
st.markdown("Behavioural anomaly detection + coordinated evidence + deterministic precision gate.")

# Discover Datasets
registry_list = datasets.discover_datasets()
registry = {d["name"]: d for d in registry_list}
if not registry:
    st.error("No datasets found in data/ or data/Traindata/")
    st.stop()

ds_names = list(registry.keys())
selected_name = st.selectbox("Select Dataset", ds_names)
ds_info = registry[selected_name]
st.session_state.selected_dataset = ds_info

st.markdown(f"**Dataset**: {ds_info['path']}")
meta = datasets.load_dataset_metadata(ds_info["path"])

# Basic stats
col1, col2, col3, col4 = st.columns(4)
col1.metric("Rows", meta.get("rows", "Unknown"))
col2.metric("Accounts", meta.get("accounts", "Unknown"))
col3.metric("Labeled", "Yes" if meta.get("has_truth") else "No")
col4.metric("Date Range", meta.get("time_range", "Unknown"))

st.markdown(f"**Capabilities Detected**: {', '.join([k for k, v in meta.get('capabilities', {}).items() if v])}")

st.markdown("---")

run_cols = st.columns(2)
run_btn = run_cols[0].button("RUN TRACE-FX", type="primary")

if run_cols[1].button("START JUDGE DEMO", type="secondary"):
    st.info("Demo Sequence: Mission Control -> Investigate -> Fraud Networks -> Temporal Replay -> Detection Quality -> How TRACE-FX Works -> Data & System")

if run_btn and st.session_state.selected_dataset:
    ds_path = st.session_state.selected_dataset["path"]
    
    st.markdown("### Engine Execution")
    
    status_placeholder = st.empty()
    log_placeholder = st.empty()
    
    # S1-S9 mapping
    stage_texts = {
        "schema": "S1 INGEST: Parsing timestamps, validating required fields, detecting available entity columns and checking data quality.",
        "features": "S2 FEATURES: Constructing past-only velocity, amount deviation, novelty, peer deviation and drift features.",
        "baseline": "S3 NORMAL BEHAVIOUR: Isolation Forest measures behavioural abnormality. This score is evidence only and cannot independently produce FRAUD.",
        "graph": "S4 GRAPH: Connecting accounts, devices, IPs, payees, merchants and transactions with timestamped relationships while suppressing high-degree shared infrastructure.",
        "motifs": "S5 MOTIFS: Testing M1 shared infrastructure, M2 common sinks, M3 pass-throughs, M4 sequence cohorts and M5 bursts.",
        "ledger": "S6 LEDGER: Converting signals into auditable positive and exculpatory evidence.",
        "gate": "S7 GATE: Requiring sufficient net evidence and independent structural evidence before FRAUD is allowed.",
        "rollup": "S8 ROLLUP: Aggregating transaction evidence into account risk and evidence-linked groups.",
        "explain": "S9 EXPLAIN: Generating deterministic explanation, causal alert timestamp and recommended action."
    }
    
    start_time = time.time()
    
    def on_progress(event):
        stage = event.get("stage", "")
        name = event.get("name", "")
        status = event.get("status", "")
        elapsed = event.get("elapsed", 0.0)
        if status == "running":
            desc = stage_texts.get(name, f"Running {name}...")
            status_placeholder.markdown(f"**{stage} {desc}**\n*(Running...)*")
        elif status == "done":
            desc = stage_texts.get(name, f"{name} complete.")
            status_placeholder.markdown(f"**{stage} {desc}**\n*(Elapsed: {elapsed:.2f}s)*")
        
    with st.spinner("Executing TRACE-FX Pipeline..."):
        df = schema.load(ds_path)
        res = engine_api.run_pipeline(df, on_event=on_progress)
        
    total_elapsed = time.time() - start_time
    st.session_state.run_result = res
    st.session_state.run_time = total_elapsed
    
    status_placeholder.success(f"Pipeline complete in {total_elapsed:.2f}s")

if "run_result" in st.session_state and st.session_state.run_result:
    res = st.session_state.run_result
    st.markdown("### Results Summary")
    
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("TRANSACTIONS", len(res.tx))
    c2.metric("ACCOUNTS", len(res.accounts))
    c3.metric("FRAUD", len(res.accounts[res.accounts["label"] == "FRAUD"]))
    c4.metric("REVIEW", len(res.accounts[res.accounts["label"] == "REVIEW"]))
    c5.metric("LEGIT", len(res.accounts[res.accounts["label"] == "LEGIT"]))
    c6.metric("SUSPICIOUS GROUPS", len(res.groups))
    
    st.markdown("---")
    st.markdown("### TOP INVESTIGATION")
    
    if not res.accounts.empty:
        top_acc = res.accounts.iloc[0]
        acc_id = top_acc["account_id"]
        
        # res.decisions is keyed by tx_id, so find a tx for this account
        txs = res.tx[res.tx["payer_id"] == acc_id]
        if not txs.empty:
            first_tx = txs.iloc[0]["tx_id"]
            dec = res.decisions[first_tx]
            
            tc1, tc2, tc3, tc4 = st.columns(4)
            tc1.markdown(f"**Account**: `{acc_id}`")
            tc2.markdown(f"**Risk**: {dec.risk:.2f}")
            tc3.markdown(f"**Net Evidence**: {dec.net_points}")
            tc4.markdown(f"**Action**: {dec.action}")
            
            if st.button("OPEN INVESTIGATION", type="primary"):
                st.session_state.investigate_target = acc_id
                st.switch_page("pages/03_investigate.py")
