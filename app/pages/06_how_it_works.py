import streamlit as st

st.title("How it Works & PS04")
st.markdown("Interactive proof matrix and pipeline architecture.")

tab1, tab2 = st.tabs(["Architecture", "PS04 Proof Matrix"])

with tab1:
    st.markdown("""
    ### TRACE-FX Pipeline
    
    1. **INGEST**: Canonicalize transaction schema.
    2. **LEARN NORMAL BEHAVIOUR**: Rolling features & anomaly detection.
    3. **BUILD TEMPORAL GRAPH**: Entities and relationships.
    4. **DETECT STRUCTURE**: Mine M1-M5 motifs.
    5. **EVIDENCE LEDGER**: Accumulate points.
    6. **PRECISION GATE**: Require multiple independent signals.
    7. **DECISION**: FRAUD / REVIEW / LEGIT.
    8. **ROLL UP**: Account risk and network topology.
    9. **CAUSAL REPLAY**: Demonstrate alert timestamp.
    """)
    
with tab2:
    st.markdown("### PS04 Requirement Coverage")
    st.markdown("""
    | Requirement | Status | Proof in App |
    |---|---|---|
    | 01 Learn normal behaviour | ✅ VERIFIED | Visible in Investigation (Behaviour Score) |
    | 02 Spot unusual behaviour | ✅ VERIFIED | High risk transactions flagged |
    | 03 Find coordinated fraud rings | ✅ VERIFIED | Fraud Rings page |
    | 04 Transaction risk | ✅ VERIFIED | Case Queue |
    | 05 Account risk | ✅ VERIFIED | Account Rollup |
    | 06 Suspicious accounts together | ✅ VERIFIED | Ring visualization |
    | 07 Pattern discovered | ✅ VERIFIED | M1-M5 Motifs |
    | 08 Connection diagram | ✅ VERIFIED | Network graph |
    | 09 Action to take | ✅ VERIFIED | Action policy output |
    | 10 False-positive control | ✅ VERIFIED | Precision Gate |
    | 11 Explain every risk score | ✅ VERIFIED | Evidence Ledger |
    | 12 Find most fraud | ✅ VERIFIED | Scorecard (Recall) |
    | 13 Rank correctly | ✅ VERIFIED | Scorecard (PR-AUC, P@10) |
    | 14 Avoid legitimate high-value | ✅ VERIFIED | Scorecard (FP count) |
    | 15 New patterns/accounts | ✅ VERIFIED | Cold start evidence logic |
    """)
