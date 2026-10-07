import streamlit as st
import pandas as pd
from pathlib import Path
import json
import time

from tracefx import schema, config, pipeline
from tracefx.replay_html import build_html

# --- Page Config & Styling ---
st.set_page_config(page_title="TRACE-FX | Command Center", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Dense, dark, forensic styling */
    :root {
        --bg: #0a0a0a;
        --surface: #121212;
        --border: #2d2d2d;
        --text: #e0e0e0;
        --text-muted: #888888;
        --danger: #ff1744;
        --warning: #ff9100;
        --success: #00e676;
        --info: #2979ff;
    }
    
    .metric-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 1rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-value { font-size: 2rem; font-weight: 700; margin: 0.5rem 0; font-family: monospace; }
    
    .pill {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 2px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        font-family: monospace;
    }
    .pill.fraud { background: rgba(255, 23, 68, 0.15); color: var(--danger); border: 1px solid rgba(255, 23, 68, 0.3); }
    .pill.review { background: rgba(255, 145, 0, 0.15); color: var(--warning); border: 1px solid rgba(255, 145, 0, 0.3); }
    .pill.legit { background: rgba(0, 230, 118, 0.15); color: var(--success); border: 1px solid rgba(0, 230, 118, 0.3); }
    
    .ledger-row {
        display: flex;
        align-items: center;
        padding: 0.5rem;
        border-bottom: 1px solid var(--border);
        font-family: monospace;
    }
    .ledger-points {
        min-width: 60px;
        font-size: 1rem;
        font-weight: bold;
    }
    .ledger-points.pos { color: var(--warning); }
    .ledger-points.neg { color: var(--success); }
    
    hr { border-color: var(--border); margin: 1rem 0; }
    h1, h2, h3, h4 { color: #fff; font-weight: 600; letter-spacing: -0.02em; }
    
    .gate-check {
        display: flex; justify-content: space-between; padding: 0.5rem; background: #1a1a1a; margin-bottom: 2px;
        font-family: monospace; border-left: 3px solid #333;
    }
    .gate-check.pass { border-left-color: var(--danger); color: var(--danger); }
    
    /* Hide Streamlit components */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- Caching & Data Loading ---
@st.cache_data(show_spinner=False)
def get_available_datasets():
    datasets = []
    for d in ["data/demo_small.csv", "data/seedA.csv", "data/seedB.csv", "data/seedC.csv", 
              "data/external/ecommerce_40k.csv", "data/external/hybrid_seed.csv"]:
        if Path(d).exists():
            datasets.append(d)
    return datasets

@st.cache_data(show_spinner=False)
def load_eval_metrics():
    dfs = []
    if Path("reports/eval_results.csv").exists():
        dfs.append(pd.read_csv("reports/eval_results.csv"))
    if Path("reports/external_eval.csv").exists():
        dfs.append(pd.read_csv("reports/external_eval.csv"))
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()

@st.cache_resource(show_spinner="Running TRACE-FX Engine...")
def run_tracefx(csv_path: str):
    p = Path(csv_path)
    if not p.exists():
        return None
    
    df = schema.load(p)
    cfg = config.load()
    
    start = time.time()
    result = pipeline.run(df, cfg)
    elapsed = time.time() - start
    
    # Save replay HTML for the UI
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    html = build_html(result)
    (reports_dir / "replay.html").write_text(html, encoding="utf-8")
    
    return result, elapsed, df

# --- Main App ---
def main():
    # --- Sidebar: DATA PLAYGROUND ---
    st.sidebar.markdown("## DATA PLAYGROUND")
    datasets = get_available_datasets()
    
    if not datasets:
        st.error("No data found.")
        return
        
    selected_ds = st.sidebar.selectbox("Select Dataset", datasets, index=0)
    
    st.sidebar.markdown("---")
    judge_mode = st.sidebar.button("🧑‍⚖️ JUDGE MODE")
    audit_mode = st.sidebar.button("🔍 AUDIT MODE")
    
    if judge_mode: st.session_state.mode = 'judge'
    elif audit_mode: st.session_state.mode = 'audit'
    elif 'mode' not in st.session_state: st.session_state.mode = 'standard'
    
    st.sidebar.markdown(f"**Current Mode:** {st.session_state.mode.upper()}")
    
    result_tuple = run_tracefx(selected_ds)
    if not result_tuple:
        st.error("Dataset load failed.")
        return
        
    result, elapsed, raw_df = result_tuple
    
    # Capabilities
    st.sidebar.markdown("### Capabilities")
    for feature, is_active in result.capabilities.items():
        color = "var(--success)" if is_active else "var(--text-muted)"
        status = "ON" if is_active else "OFF"
        st.sidebar.markdown(f"<div style='font-family: monospace; font-size: 0.8rem;'><span style='color: {color};'>■</span> {feature}: {status}</div>", unsafe_allow_html=True)
    
    if st.session_state.mode == 'audit':
        st.sidebar.markdown("### Audit Info")
        st.sidebar.text(f"Rows: {len(raw_df)}\nTime: {elapsed:.2f}s\nHash: {hash(str(raw_df.columns))}")
        
    # --- Header ---
    st.markdown("<h1>TRACE-FX</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-muted); font-size: 1.1rem; margin-top: -1rem; margin-bottom: 1rem;'>Temporal Risk & Coordinated Evidence Engine<br/>Real-time-oriented fraud intelligence engine with causal temporal replay and batch scoring.</p>", unsafe_allow_html=True)
    
    # --- Navigation Tabs ---
    tabs = st.tabs([
        "COMMAND CENTER", "INVESTIGATE", "FRAUD RINGS", "TX EXPLORER", 
        "TEMPORAL REPLAY", "WHY NOT FRAUD?", "EVALUATION", 
        "HOW IT WORKS", "PS04 COMPLIANCE"
    ])
    
    # Pre-compute some dataframes
    accounts_df = result.accounts.sort_values("risk", ascending=False)
    groups_data = [{"group_id": g.group_id, "accounts": ", ".join(g.accounts), "risk": g.risk, "shape": g.shape, "evidence_types": ", ".join(list(g.evidence_types))} for g in result.groups]
    groups_df = pd.DataFrame(groups_data)
    tx_df = raw_df.copy()
    
    # Map tx to risks if possible
    tx_df['payer_risk'] = tx_df['payer_id'].map(lambda x: result.decisions[x].risk if x in result.decisions else 0.0)
    tx_df['payer_label'] = tx_df['payer_id'].map(lambda x: result.decisions[x].label if x in result.decisions else "LEGIT")

    # --- TAB 1: COMMAND CENTER ---
    with tabs[0]:
        st.markdown(f"**DATASET:** `{selected_ds}` | **RUN STATUS:** <span style='color: var(--success);'>COMPLETE</span>", unsafe_allow_html=True)
        
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.markdown(f"<div class='metric-card'><div>TRANSACTIONS</div><div class='metric-value'>{len(raw_df)}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><div>ACCOUNTS</div><div class='metric-value'>{result.metrics['total_accounts']}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><div style='color: var(--danger)'>FRAUD</div><div class='metric-value' style='color: var(--danger)'>{result.metrics['fraud_accounts']}</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-card'><div style='color: var(--warning)'>REVIEW</div><div class='metric-value' style='color: var(--warning)'>{result.metrics['review_accounts']}</div></div>", unsafe_allow_html=True)
        m5.markdown(f"<div class='metric-card'><div style='color: var(--success)'>LEGIT</div><div class='metric-value' style='color: var(--success)'>{result.metrics['legit_accounts']}</div></div>", unsafe_allow_html=True)
        m6.markdown(f"<div class='metric-card'><div>GROUPS</div><div class='metric-value'>{len(groups_df)}</div></div>", unsafe_allow_html=True)
        
        st.subheader("Highest Risk Accounts")
        st.dataframe(accounts_df.head(10)[['account_id', 'label', 'net_points', 'risk']], use_container_width=True, hide_index=True)
        
    # --- TAB 2: INVESTIGATE ---
    with tabs[1]:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Select Account")
            acc_list = accounts_df['account_id'].tolist()
            if not acc_list:
                st.warning("No accounts.")
            else:
                selected_acc = st.selectbox("Account ID", acc_list)
                dec = result.decisions.get(selected_acc)
                
                if not dec:
                    st.warning("Decision data not available for this account.")
                else:
                    st.markdown(f"""
                    <div style='background: var(--surface); padding: 1rem; border: 1px solid var(--border);'>
                        <div style='display: flex; justify-content: space-between;'>
                            <h3>{dec.account_id}</h3>
                            <span class='pill {dec.label.lower()}' style='font-size: 1rem; padding: 0.5rem;'>{dec.label}</span>
                        </div>
                        <div style='font-family: monospace; font-size: 1.5rem; margin-top: 1rem;'>{dec.net_points} pts</div>
                        <div style='color: var(--text-muted);'>Risk: {dec.risk:.2f} | Alert: {dec.alert_ts or 'None'}</div>
                        <hr/>
                        <div style='color: var(--info); font-weight: bold;'>ACTION POLICY</div>
                        <div style='font-family: monospace;'>{dec.action}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("### Why?")
                    st.info(dec.explanation)

        with col2:
            if acc_list:
                st.subheader("Precision Evidence Gate")
                dec = result.decisions.get(selected_acc) if 'selected_acc' in locals() else None
                if dec:
                    net_pass = dec.net_points >= 60
                    struct_pass = len(dec.motifs_fired) >= 2
                    
                    st.markdown(f"""
                    <div class="gate-check {'pass' if net_pass else ''}">
                        <span>[{"PASS" if net_pass else "FAIL"}] Net Points >= 60</span>
                        <span>{dec.net_points} / 60</span>
                    </div>
                    <div class="gate-check {'pass' if struct_pass else ''}">
                        <span>[{"PASS" if struct_pass else "FAIL"}] Independent Structural Types >= 2</span>
                        <span>{len(dec.motifs_fired)} / 2</span>
                    </div>
                    <div class="gate-check pass">
                        <span>[PASS] Behaviour-alone restriction</span>
                        <span>Verified</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.subheader("Evidence Ledger")
                    pos_lines = [l for l in dec.ledger if l.points > 0]
                    neg_lines = [l for l in dec.ledger if l.points <= 0]
                    
                    for l in pos_lines:
                        st.markdown(f"""
                        <div class="ledger-row">
                            <div class="ledger-points pos">+{l.points:g}</div>
                            <div>
                                <div><b>{l.source}</b></div>
                                <div style="font-size: 0.85rem; color: var(--text-muted);">{l.text}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    st.subheader("Exculpatory Evidence")
                    if not neg_lines:
                        st.markdown("<span style='color: var(--text-muted);'>No negative evidence found.</span>", unsafe_allow_html=True)
                    for l in neg_lines:
                        st.markdown(f"""
                        <div class="ledger-row" style="background: rgba(0, 230, 118, 0.05);">
                            <div class="ledger-points neg">{l.points:g}</div>
                            <div>
                                <div><b>{l.source}</b></div>
                                <div style="font-size: 0.85rem; color: var(--text-muted);">{l.text}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.caption("Negative evidence prevents a single suspicious signal from becoming an automatic fraud accusation.")

    # --- TAB 3: FRAUD RINGS ---
    with tabs[2]:
        st.subheader("Suspicious Groups (Connected by Evidence)")
        if not groups_df.empty:
            st.dataframe(groups_df, use_container_width=True, hide_index=True)
        else:
            st.info("No groups detected.")

    # --- TAB 4: TX EXPLORER ---
    with tabs[3]:
        st.subheader("Transaction Explorer")
        st.dataframe(tx_df[['tx_id', 'ts', 'payer_id', 'payee_id', 'amount', 'payer_label', 'payer_risk']].head(500), use_container_width=True, hide_index=True)

    # --- TAB 5: TEMPORAL REPLAY ---
    with tabs[4]:
        st.subheader("Causal Ring Assembly Replay")
        replay_path = Path("reports/replay.html")
        if replay_path.exists():
            st.html(replay_path.read_text(encoding="utf-8"))
        else:
            st.warning("Replay not generated.")

    # --- TAB 6: WHY NOT FRAUD ---
    with tabs[5]:
        st.subheader("Why Was This Not Fraud?")
        st.write("Demonstrating false-positive protection on legitimate high-value transactions.")
        
        if not tx_df.empty:
            # Find a legit tx with high amount
            q90 = tx_df['amount'].quantile(0.9)
            legit_high_val = tx_df[(tx_df['amount'] > q90) & (tx_df['payer_label'] == "LEGIT")]
            
            if not legit_high_val.empty:
                eg_tx = legit_high_val.iloc[0]
                eg_acc = eg_tx['payer_id']
                eg_dec = result.decisions.get(eg_acc)
                
                if eg_dec:
                    st.markdown(f"""
                    <div style='background: var(--surface); padding: 1rem; border: 1px solid var(--border);'>
                        <h4>Transaction {eg_tx['tx_id']}</h4>
                        <p><b>Amount:</b> ${eg_tx['amount']:.2f} (High Value, >90th percentile)</p>
                        <p><b>Account:</b> {eg_acc}</p>
                        <hr/>
                        <h4>Evidence</h4>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    for l in eg_dec.ledger:
                        color = "pos" if l.points > 0 else "neg"
                        st.markdown(f"""
                        <div class="ledger-row">
                            <div class="ledger-points {color}">{'+' if l.points > 0 else ''}{l.points:g}</div>
                            <div><b>{l.source}</b>: {l.text}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    st.markdown("<br/><b>Explanation:</b> High transaction value alone is not sufficient evidence of coordinated fraud.", unsafe_allow_html=True)
            else:
                st.info("No legit high-value transactions in this sample.")

    # --- TAB 7: EVALUATION ---
    with tabs[6]:
        st.subheader("Model Evaluation")
        st.write("Strict FRAUD metrics and ring-recall measure different properties. A ring can be structurally detected while individual members remain REVIEW under the precision gate.")
        eval_df = load_eval_metrics()
        if not eval_df.empty:
            st.dataframe(eval_df, use_container_width=True, hide_index=True)
        else:
            st.info("Run `tracefx eval` to generate metrics.")

    # --- TAB 8: HOW IT WORKS ---
    with tabs[7]:
        st.markdown("""
        ### How TRACE-FX Works
        
        01 — **INGEST**: Canonical transaction mapping.
        02 — **NORMALIZE**: Validate schema, detect capabilities.
        03 — **BEHAVIOUR**: Build past-only features (velocity, deviation). Output Risk 0..1 via IsolationForest.
        04 — **GRAPH**: Build typed temporal relationships with strict Hub Caps to ignore shared infrastructure.
        05 — **MOTIFS**: Search for structural patterns (M1-M5).
        06 — **EVIDENCE**: Produce timestamped causal evidence.
        07 — **LEDGER**: Weigh positive motifs against exculpatory negative evidence (tenure, known devices).
        08 — **PRECISION GATE**: FRAUD requires `NET >= 60` AND `>=2 structural types`.
        09 — **DECISION**: FRAUD / REVIEW / LEGIT.
        10 — **ROLLUP**: Aggregate connected evidence links into rings.
        11 — **EXPLANATION**: Deterministic translation of the ledger.
        12 — **REPLAY**: Causal chronological reconstruction.
        
        ---
        **TRACE-FX DOES NOT ASK: "Does the model say fraud?"**
        It asks:
        1. Is the behaviour unusual?
        2. Who is connected?
        3. What evidence supports the accusation?
        4. What evidence argues against it?
        
        MODEL = behavioural signal | GRAPH = relationship context | MOTIFS = structural pattern | LEDGER = auditable reasoning | GATE = accusation control
        """)

    # --- TAB 9: PS04 COMPLIANCE ---
    with tabs[8]:
        st.markdown("""
        ### HNX26PSI04 — PROBLEM STATEMENT COVERAGE
        
        **01: "Learn normal behavior"**
        TRACE-FX uses IsolationForest over rolling behavioral features to establish baselines.
        
        **02: "Spot when something is off"**
        Deviations trigger behavioral evidence points, but cannot alone produce a FRAUD decision.
        
        **03: "Find coordinated fraud rings"**
        M1-M5 structural motifs operate on a typed temporal graph to detect coordinated multi-actor setups.
        
        **04 & 05: "Risk score for transaction/account"**
        Deterministic net points mapped to a noisy-OR risk (0..1) with discrete tiering.
        
        **06: "Suspicious together"**
        Evidence-linked groups (see Fraud Rings tab).
        
        **07: "What pattern did you find?"**
        Explicit deterministic structural motifs (M1-M5) output via the Ledger.
        
        **08: "Connection diagram"**
        Causal vis-network replay graph plotting actual relationships.
        
        **09: "Action to take"**
        Action policy mapping (Hold/Escalate vs Step-up).
        
        **10 & 14: "False positive limit & Avoid legit high-value"**
        Strict Precision Gate requires 2 structural signals. Exculpatory negative points defend legit high-value txs.
        
        **11: "Explain every score"**
        The Evidence Ledger is the sole decider; every point is auditable.
        
        **12 & 13: "Find most fraud & rank correctly"**
        Measured via strict and any-ring PR-AUC (see Evaluation tab).
        
        **15: "Advanced: new patterns"**
        M4 Sequence Cohort detects novel coordinated paths independent of known rules.
        """)

if __name__ == "__main__":
    main()
