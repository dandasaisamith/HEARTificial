"""Streamlit frontend for TRACE-FX."""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
import networkx as nx
import time

from tracefx import config, schema, pipeline
from tracefx.replay_html import build_html

st.set_page_config(
    page_title="TRACE-FX | Fraud Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a premium dark mode, dynamic aesthetics
st.markdown("""
<style>
    :root {
        --primary: #00E5FF;
        --danger: #FF1744;
        --warning: #FF9100;
        --success: #00E676;
        --bg: #0F141E;
        --surface: #1E2532;
        --border: #2D3748;
        --text: #E2E8F0;
        --text-muted: #94A3B8;
    }
    
    .stApp {
        background-color: var(--bg);
        color: var(--text);
    }
    
    .metric-card {
        background-color: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(0, 229, 255, 0.1);
        border-color: rgba(0, 229, 255, 0.3);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FFF 0%, var(--primary) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .ledger-row {
        padding: 1rem;
        border-bottom: 1px solid var(--border);
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .ledger-points.positive { color: var(--danger); font-weight: bold; font-size: 1.2rem; min-width: 60px; }
    .ledger-points.negative { color: var(--success); font-weight: bold; font-size: 1.2rem; min-width: 60px; }
    
    .pill {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.875rem;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .pill.fraud { background: rgba(255, 23, 68, 0.1); color: var(--danger); border: 1px solid rgba(255, 23, 68, 0.2); }
    .pill.review { background: rgba(255, 145, 0, 0.1); color: var(--warning); border: 1px solid rgba(255, 145, 0, 0.2); }
    .pill.legit { background: rgba(0, 230, 118, 0.1); color: var(--success); border: 1px solid rgba(0, 230, 118, 0.2); }
    
    hr { border-color: var(--border); }
    
    h1, h2, h3 { color: #FFF; font-weight: 600; }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_and_run(csv_path: str):
    p = Path(csv_path)
    if not p.exists():
        return None
    
    df = schema.load(p)
    cfg = config.load()
    result = pipeline.run(df, cfg)
    
    # Save replay HTML
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    html = build_html(result)
    (reports_dir / "replay.html").write_text(html, encoding="utf-8")
    
    return result

def main():
    st.title("TRACE-FX Intelligence")
    st.markdown("<p style='color: var(--text-muted); font-size: 1.2rem; margin-top: -1rem; margin-bottom: 2rem;'>Precision Fraud Defense Engine</p>", unsafe_allow_html=True)
    
    with st.spinner("Loading and processing data..."):
        result = load_and_run("data/demo_small.csv")
        
    if not result:
        st.error("No data found. Please run `make data` first.")
        return
        
    # --- Metrics Dashboard ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div style="color: var(--text-muted); font-size: 0.9rem; text-transform: uppercase;">Analyzed Accounts</div>
            <div class="metric-value">{result.metrics['total_accounts']}</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div style="color: var(--text-muted); font-size: 0.9rem; text-transform: uppercase;">Fraud Detected</div>
            <div class="metric-value" style="background: linear-gradient(135deg, #FF1744 0%, #FF8A80 100%); -webkit-background-clip: text;">{result.metrics['fraud_accounts']}</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div style="color: var(--text-muted); font-size: 0.9rem; text-transform: uppercase;">Review Required</div>
            <div class="metric-value" style="background: linear-gradient(135deg, #FF9100 0%, #FFD180 100%); -webkit-background-clip: text;">{result.metrics['review_accounts']}</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div style="color: var(--text-muted); font-size: 0.9rem; text-transform: uppercase;">Latency</div>
            <div class="metric-value" style="background: linear-gradient(135deg, #00E676 0%, #B9F6CA 100%); -webkit-background-clip: text;">{result.metrics['elapsed_s']}s</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    tab_queue, tab_replay = st.tabs(["📋 Decision Queue", "🕸️ Causal Replay Graph"])
    
    with tab_queue:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Account Queue")
            
            # Sort accounts by risk descending
            acc_df = result.accounts.sort_values("risk", ascending=False)
            
            # Create a nice selection list
            for _, row in acc_df.iterrows():
                acc_id = row['account_id']
                label = row['label']
                pts = row['net_points']
                
                label_cls = label.lower()
                
                if st.button(
                    f"{acc_id} | {label} ({pts} pts)", 
                    key=f"btn_{acc_id}",
                    use_container_width=True,
                ):
                    st.session_state.selected_account = acc_id

        with col2:
            st.subheader("Evidence Ledger")
            selected = st.session_state.get('selected_account')
            
            if not selected:
                # Default select highest risk
                if not acc_df.empty:
                    selected = acc_df.iloc[0]['account_id']
                    
            if selected and selected in result.decisions:
                dec = result.decisions[selected]
                
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; background: var(--surface); padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border);">
                    <div>
                        <h2 style="margin: 0; font-size: 2rem;">{selected}</h2>
                        <div style="color: var(--text-muted); margin-top: 0.5rem;">Causal Alert: <b>{dec.alert_ts or 'None'}</b></div>
                    </div>
                    <div style="text-align: right;">
                        <span class="pill {dec.label.lower()}" style="font-size: 1.2rem; padding: 0.5rem 1rem;">{dec.label}</span>
                        <div style="font-size: 1.5rem; font-weight: bold; margin-top: 0.5rem;">{dec.net_points} pts</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("### Action Policy")
                st.info(dec.action)
                
                st.markdown("### Decision Ledger")
                
                # Separate positive and negative points
                pos_lines = [l for l in dec.ledger if l.points > 0]
                neg_lines = [l for l in dec.ledger if l.points <= 0]
                
                for l in pos_lines:
                    st.markdown(f"""
                    <div class="ledger-row">
                        <div class="ledger-points positive">+{l.points:g}</div>
                        <div>
                            <div style="font-weight: bold;">{l.source.replace('_', ' ').title()}</div>
                            <div style="color: var(--text-muted); font-size: 0.9rem;">{l.text}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                if neg_lines:
                    st.markdown("<h4 style='margin-top: 1.5rem; color: var(--success);'>Exculpatory Evidence</h4>", unsafe_allow_html=True)
                    for l in neg_lines:
                        st.markdown(f"""
                        <div class="ledger-row" style="background: rgba(0, 230, 118, 0.05);">
                            <div class="ledger-points negative">{l.points:g}</div>
                            <div>
                                <div style="font-weight: bold;">{l.source.replace('_', ' ').title()}</div>
                                <div style="color: var(--text-muted); font-size: 0.9rem;">{l.text}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
    with tab_replay:
        st.subheader("Causal Ring Assembly Replay")
        
        replay_path = Path("reports/replay.html")
        if replay_path.exists():
            html_data = replay_path.read_text(encoding="utf-8")
            st.html(html_data)
        else:
            st.warning("Replay HTML not found. Pipeline may not have completed.")

if __name__ == "__main__":
    main()
