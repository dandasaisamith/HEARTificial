import streamlit as st
import pandas as pd
import time
from tracefx import schema, engine_api
from ui import datasets

st.title("Mission Control")
st.markdown("Select a dataset to ingest and analyze with TRACE-FX.")

# State initialization
if "selected_dataset" not in st.session_state:
    st.session_state.selected_dataset = None
if "run_result" not in st.session_state:
    st.session_state.run_result = None

# Dataset Discovery
all_datasets = datasets.discover_datasets()

cols = st.columns([2, 1])
with cols[0]:
    ds_names = [d["name"] for d in all_datasets]
    selected_name = st.selectbox("Select Dataset", ds_names)
    
    if selected_name:
        ds_info = next(d for d in all_datasets if d["name"] == selected_name)
        st.session_state.selected_dataset = ds_info
        
with cols[1]:
    if st.session_state.selected_dataset:
        st.markdown(f"**Size**: {st.session_state.selected_dataset['size_mb']:.1f} MB")
        
        meta = datasets.load_dataset_metadata(st.session_state.selected_dataset["path"])
        if meta["status"] == "READY":
            st.markdown(f"<span class='badge badge-clear'>READY</span>", unsafe_allow_html=True)
            if meta["has_truth"]:
                st.markdown("<span class='badge badge-clear'>LABELS AVAILABLE</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span class='badge badge-review'>{meta['status']}</span>", unsafe_allow_html=True)
            
st.markdown("---")

run_cols = st.columns(2)
run_btn = run_cols[0].button("Run TRACE-FX Pipeline", type="primary")
demo_btn = run_cols[1].button("Guided Demo", type="secondary")

if demo_btn:
    st.info("Guided Demo path: Select dataset -> Run -> View Scorecard -> Investigate Rings -> Replay")

if run_btn and st.session_state.selected_dataset:
    ds_path = st.session_state.selected_dataset["path"]
    
    # Check cache
    cached_res, is_cached = engine_api.get_cached_run(ds_path)
    
    if is_cached:
        st.info("Loaded cached result in < 1s")
        st.session_state.run_result = cached_res
    else:
        st.info("Live scoring in progress...")
        
        # UI Placeholders for Pipeline execution
        st.markdown("### Live Pipeline Execution")
        
        stage_placeholders = {}
        stages_to_show = ["S1", "S2", "S4", "S5", "S6", "S7", "S8", "S9"]
        
        for stage in stages_to_show:
            stage_placeholders[stage] = st.empty()
            with stage_placeholders[stage]:
                st.markdown(f"⏳ **{stage}** - Waiting...")
                
        def on_event(ev):
            stage = ev["stage"]
            if stage in stage_placeholders:
                ph = stage_placeholders[stage]
                if ev["status"] == "running":
                    ph.markdown(f"🔄 **{stage}: {ev['name']}** - Running...")
                elif ev["status"] == "done":
                    t = ev["elapsed"]
                    met = ev.get("metrics", {})
                    met_str = " | ".join(f"{k}: {v}" for k, v in met.items())
                    ph.markdown(f"✅ **{stage}: {ev['name']}** - Done in {t:.2f}s ({met_str})")
        
        df = schema.load(ds_path)
        
        # We need the truth df for S9
        meta = datasets.load_dataset_metadata(ds_path)
        truth_df = None
        if meta["has_truth"]:
            truth_df = pd.read_json(meta["truth_path"], lines=True) if meta["truth_path"].endswith(".json") else None
            
        res = engine_api.run_pipeline(df, truth_df=truth_df, on_event=on_event)
        engine_api.save_cached_run(ds_path, res)
        st.session_state.run_result = res
        
        st.success("Run Complete!")
        
if st.session_state.run_result:
    res = st.session_state.run_result
    st.markdown("### Findings Summary")
    
    kpi_cols = st.columns(5)
    kpi_cols[0].metric("Transactions", res.metrics["total_transactions"])
    kpi_cols[1].metric("Accounts", res.metrics["total_accounts"])
    kpi_cols[2].metric("FRAUD", res.metrics["fraud_accounts"])
    kpi_cols[3].metric("REVIEW", res.metrics["review_accounts"])
    kpi_cols[4].metric("Suspicious Rings", res.metrics["groups"])

