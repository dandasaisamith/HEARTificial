import streamlit as st
import pandas as pd

st.title("Case Queue")
st.markdown("Investigate individual transactions and accounts.")

if "run_result" not in st.session_state or st.session_state.run_result is None:
    st.warning("Please run a dataset in Mission Control first.")
    st.stop()
    
res = st.session_state.run_result

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### Queue")
    # Show accounts sorted by risk
    df_acc = res.accounts.sort_values(by="risk", ascending=False)
    
    # Render table
    st.dataframe(
        df_acc[["account_id", "label", "risk", "net_points"]],
        column_config={
            "risk": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1),
        },
        use_container_width=True,
        hide_index=True
    )
    
    # Mock selection
    sel_account = st.selectbox("Select Account to Investigate", df_acc["account_id"].tolist())

with col2:
    if sel_account:
        dec = res.decisions.get(sel_account)
        if dec:
            st.markdown(f"## Account: {sel_account}")
            
            badge_class = f"badge-{dec.label.lower()}"
            st.markdown(f"<span class='badge {badge_class}'>{dec.label}</span> &nbsp; **Risk**: {dec.risk:.2f} &nbsp; **Net Evidence**: {dec.net_points}", unsafe_allow_html=True)
            
            if dec.action:
                st.markdown(f"**Action**: `{dec.action}`")
                
            st.markdown("### Evidence Ledger")
            for l in dec.ledger:
                color = "green" if l.points < 0 else "red"
                st.markdown(f"**<span style='color:{color}'>{l.points:+}</span>** {l.source}: {l.text}", unsafe_allow_html=True)
                
            st.markdown("### Precision Gate")
            st.code(f"Net Points >= 60: {dec.net_points >= 60}\nAlert TS: {dec.alert_ts}")
            
            if dec.label == "LEGIT":
                st.markdown("### 🛡️ Why Not Fraud?")
                st.markdown("TRACE-FX protects this account because:")
                missing_structure = dec.net_points >= 30 and dec.label == "LEGIT"
                if missing_structure:
                    st.markdown("❌ **Missing structural evidence**: While anomaly scores exist, there are <2 independent structural signals (M1-M5).")
                if sum(1 for l in dec.ledger if l.points < 0) > 0:
                    st.markdown("✅ **Exculpatory Evidence**: Counter-evidence points reduced the total risk score.")
                st.markdown("This prevents false positive locks on legitimate high-value behavior.")
