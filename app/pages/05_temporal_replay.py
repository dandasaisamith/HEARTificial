import streamlit as st
import pandas as pd

st.title("TEMPORAL REPLAY")
st.markdown("Causal accumulation of evidence over time. Discover exactly when TRACE-FX first had enough evidence to act.")

if "run_result" not in st.session_state or st.session_state.run_result is None:
    st.warning("Run TRACE-FX before opening an investigation.")
    st.stop()
    
res = st.session_state.run_result

if "replay_events" not in st.session_state:
    events = []
    # Base transactions
    for _, row in res.tx.iterrows():
        events.append({"ts": row["ts"], "type": "tx", "id": row["tx_id"], "desc": f"Transaction {row['tx_id']} from {row['payer_id']}"})
    
    # Evidence satisfied
    for ev in res.evidence:
        events.append({"ts": ev.satisfied_at, "type": "evidence", "id": ev.type, "desc": f"Structural Evidence: {ev.type.upper()}"})
        
    # Alerts
    for acc_id, dec in res.decisions.items():
        if dec.label in ("FRAUD", "REVIEW"):
            events.append({"ts": dec.alert_ts, "type": "alert", "id": acc_id, "desc": f"PRECISION GATE PASSED: {dec.label} on {acc_id}"})
            
    events.sort(key=lambda x: pd.to_datetime(x["ts"]))
    st.session_state.replay_events = events
    st.session_state.replay_idx = 0
    st.session_state.playing = False

events = st.session_state.replay_events
if not events:
    st.info("No events to replay.")
    st.stop()

st.markdown("---")
c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
if c1.button("▶ PLAY" if not st.session_state.playing else "⏸ PAUSE"):
    st.session_state.playing = not st.session_state.playing
    st.rerun()

if c2.button("⏮ RESTART"):
    st.session_state.replay_idx = 0
    st.session_state.playing = False
    st.rerun()
    
if c3.button("⏭ NEXT"):
    st.session_state.replay_idx = min(len(events) - 1, st.session_state.replay_idx + 1)
    st.rerun()

idx = st.slider("Timeline", 0, len(events) - 1, st.session_state.replay_idx, key="slider_idx", label_visibility="collapsed")
if idx != st.session_state.replay_idx:
    st.session_state.replay_idx = idx

@st.fragment(run_every=0.5 if st.session_state.playing else None)
def render_replay():
    if st.session_state.playing:
        if st.session_state.replay_idx < len(events) - 1:
            st.session_state.replay_idx += 1
            st.rerun()
        else:
            st.session_state.playing = False
            st.rerun()
            
    current_idx = st.session_state.replay_idx
    ev = events[current_idx]
    
    st.markdown(f"### CURRENT TIMESTAMP: `{ev['ts']}`")
    
    if ev["type"] == "alert":
        st.error(f"🚨 **CAUSAL ALERT TIME**: {ev['desc']}")
        st.info("Alert time is the first timestamp at which the evidence required by the decision gate was satisfied.")
    elif ev["type"] == "evidence":
        st.warning(f"⚠️ **EVIDENCE GATHERED**: {ev['desc']}")
    else:
        st.success(f"✅ **EVENT**: {ev['desc']}")

    st.markdown("**Live Event Feed**")
    start = max(0, current_idx - 5)
    for i in range(current_idx, start - 1, -1):
        e = events[i]
        color = "gray"
        if e["type"] == "alert": color = "var(--fraud)"
        elif e["type"] == "evidence": color = "var(--review)"
        
        st.markdown(f"<div style='border-left: 3px solid {color}; padding-left: 10px; margin-bottom: 5px;'>"
                    f"<small>{e['ts']}</small><br>{e['desc']}</div>", unsafe_allow_html=True)
                        
render_replay()
