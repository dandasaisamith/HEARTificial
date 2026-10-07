import streamlit as st
import pandas as pd
import time

st.title("Temporal Replay")
st.markdown("Causal accumulation of evidence over time.")

if "run_result" not in st.session_state or st.session_state.run_result is None:
    st.warning("Please run a dataset in Mission Control first.")
    st.stop()
    
res = st.session_state.run_result

# 1. Precompute Events
if "replay_events" not in st.session_state:
    events = []
    # tx events
    for _, row in res.tx.iterrows():
        events.append({"ts": row["ts"], "type": "tx", "id": row["tx_id"], "desc": f"Transaction {row['tx_id'][-8:]} from {row['payer_id'][-8:]}"})
    # evidence events
    for ev in res.evidence:
        events.append({"ts": ev.satisfied_at, "type": "evidence", "id": ev.type, "desc": f"Motif {ev.type} satisfied for {len(ev.accounts)} accounts"})
    # decision events
    for acc_id, dec in res.decisions.items():
        if dec.label in ("FRAUD", "REVIEW"):
            events.append({"ts": dec.alert_ts, "type": "alert", "id": dec.tx_id, "desc": f"{dec.label} alert on {acc_id[-8:]}"})
            
    # Sort
    events.sort(key=lambda x: pd.to_datetime(x["ts"]))
    st.session_state.replay_events = events
    st.session_state.replay_idx = 0
    st.session_state.playing = False

events = st.session_state.replay_events

if not events:
    st.info("No events to replay.")
    st.stop()

# Controls
c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
if c1.button("▶ Play" if not st.session_state.playing else "⏸ Pause"):
    st.session_state.playing = not st.session_state.playing
    st.rerun()

if c2.button("⏮ Restart"):
    st.session_state.replay_idx = 0
    st.session_state.playing = False
    st.rerun()
    
if c3.button("⏭ Step"):
    st.session_state.replay_idx = min(len(events) - 1, st.session_state.replay_idx + 1)
    st.rerun()

idx = st.slider("Timeline", 0, len(events) - 1, st.session_state.replay_idx, key="slider_idx")
if idx != st.session_state.replay_idx:
    st.session_state.replay_idx = idx

@st.fragment(run_every=0.5 if st.session_state.playing else None)
def render_replay():
    if st.session_state.playing:
        if st.session_state.replay_idx < len(events) - 1:
            st.session_state.replay_idx += 1
            # Rerun the fragment to update immediately
            st.rerun()
        else:
            st.session_state.playing = False
            st.rerun()
            
    current_idx = st.session_state.replay_idx
    ev = events[current_idx]
    
    st.markdown(f"### Current Time: `{ev['ts']}`")
    st.progress((current_idx + 1) / len(events))
    
    col_l, col_r = st.columns([2, 1])
    
    with col_r:
        st.markdown("**Live Event Feed**")
        # show last 10 events
        start = max(0, current_idx - 9)
        for i in range(current_idx, start - 1, -1):
            e = events[i]
            color = "gray"
            if e["type"] == "alert": color = "var(--fraud)"
            elif e["type"] == "evidence": color = "var(--ring)"
            
            st.markdown(f"<div style='border-left: 3px solid {color}; padding-left: 10px; margin-bottom: 5px;'>"
                        f"<small>{e['ts']}</small><br>{e['desc']}</div>", unsafe_allow_html=True)
                        
    with col_l:
        st.markdown("**Graph State**")
        st.info("Dynamic graph state up to this timestamp goes here.")
        
render_replay()
