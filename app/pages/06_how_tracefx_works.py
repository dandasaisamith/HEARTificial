import streamlit as st

st.title("HOW TRACE-FX WORKS")
st.markdown("PS04 Proof Matrix & Interactive Pipeline Architecture.")

tab1, tab2 = st.tabs(["PS04 Proof Matrix", "Interactive Pipeline"])

with tab1:
    st.markdown("### PS04 Requirement Coverage")
    st.markdown("""
    | PS04 Requirement | How TRACE-FX Addresses It | Live Proof Location |
    |---|---|---|
    | **01 Learn normal behaviour** | Fits an Isolation Forest per account over rolling features. | **INVESTIGATE** (Behavioural Evidence section) |
    | **02 Spot unusual behaviour** | Z-score deviations & feature novelty thresholding. | **INVESTIGATE** (Isolation Forest score) |
    | **03 Find coordinated fraud rings** | NetworkX Hub-Capped Graph -> M1-M5 Motif Extractors. | **FRAUD NETWORKS** (Topology) |
    | **04 Transaction risk** | Evaluated via causal graph connection & behaviour at `ts`. | **INVESTIGATE** (Case Queue) |
    | **05 Account risk** | Noisy-OR aggregation of points in Evidence Ledger. | **MISSION CONTROL** (Account rollups) |
    | **06 Suspicious accounts together** | Connected components built *only* across evidence links. | **FRAUD NETWORKS** (Ring Selection) |
    | **07 Pattern discovered** | Specific structural mapping (M1 Shared Device, M2 Sink, etc). | **INVESTIGATE** (Evidence Ledger details) |
    | **08 Connection diagram** | Plotly NetworkX topological rendering. | **FRAUD NETWORKS** (Interactive Graph) |
    | **09 Action to take** | Deterministic mapping based on Decision & Motif. | **INVESTIGATE** (Action Field) |
    | **10 False-positive control** | Exculpatory logic + Structural gate requirement. | **INVESTIGATE** (Why Not Fraud? section) |
    | **11 Explain every risk score** | Human-readable balance sheet of +/- points. | **INVESTIGATE** (Evidence Ledger) |
    | **12 Find most fraud** | Any-Ring Recall tracking & tuning. | **DETECTION QUALITY** (Recall metrics) |
    | **13 Rank correctly** | Points mapped to Risk (PR-AUC, P@10). | **DETECTION QUALITY** (Ranking Quality) |
    | **14 Protect legit high-value** | Counter-evidence blocks behaviour-only flags. | **INVESTIGATE** (Why Not Fraud?) |
    | **15 Advanced/new patterns** | M4 Sequence Cohorts dynamically catch item flash-sales. | **FRAUD NETWORKS** (M4 Motif chips) |
    """)

with tab2:
    st.markdown("### 01 INGEST")
    st.markdown("**What**: Canonicalizes CSVs, drops missing, casts timestamps to UTC int64 ns.\n**Input**: Raw CSV\n**Output**: Typed DataFrame\n**Module**: `tracefx.schema`\n**PS04**: Enables global offline correlation.")
    
    st.markdown("### 02 NORMALIZE & 03 BUILD FEATURES")
    st.markdown("**What**: Constructs rolling 1h/24h velocity, amount deviations, new-entity flags.\n**Input**: Sorted DataFrame\n**Output**: Feature Matrix\n**Module**: `tracefx.features`\n**PS04**: Contextualizes every transaction.")
    
    st.markdown("### 04 LEARN NORMAL")
    st.markdown("**What**: Isolation Forest fits over features to yield an anomaly probability.\n**Input**: Features\n**Output**: Anomaly Score `0..1`\n**Module**: `tracefx.baseline`\n**PS04**: Detects purely behavioral deviations.")
    
    st.markdown("### 05 BUILD GRAPH")
    st.markdown("**What**: MultiGraph linking Payer->Payee, Device, IP with Hub Caps (>8 dropped).\n**Input**: Transactions\n**Output**: `networkx.MultiGraph`\n**Module**: `tracefx.graph`\n**PS04**: Prevents shared-infrastructure false positives.")
    
    st.markdown("### 06 MINE M1-M5")
    st.markdown("**What**: Exact causal structural mining (M1 Shared Device, M2 Sink, M3 Pass-Through, M4 Cohort, M5 Burst).\n**Input**: Graph & Transactions\n**Output**: `Evidence` objects\n**Module**: `tracefx.motifs`\n**PS04**: Finds coordinated rings mathematically.")
    
    st.markdown("### 07 BUILD EVIDENCE & 08 APPLY COUNTER-EVIDENCE")
    st.markdown("**What**: Positive points for motifs/behavior, negative for tenure/repeats.\n**Input**: Evidence & Scores\n**Output**: `LedgerLine` array\n**Module**: `tracefx.ledger`\n**PS04**: Explainable balance-sheet scoring.")
    
    st.markdown("### 09 PRECISION GATE & 10 DECIDE")
    st.markdown("**What**: Requires `net_points >= 60` AND `structural_motifs >= 2`.\n**Input**: Ledger\n**Output**: `Decision` (FRAUD/REVIEW/LEGIT)\n**Module**: `tracefx.gate`\n**PS04**: Stops high-value false positives dead.")
    
    st.markdown("### 11 ROLL UP & 12 EXPLAIN")
    st.markdown("**What**: Groups evidence-linked accounts and auto-generates text.\n**Input**: Decisions\n**Output**: `Group` and Explanations\n**Module**: `tracefx.rollup`, `tracefx.explain`\n**PS04**: Creates the final investigation dossier.")
    
    st.markdown("### 13 REPLAY")
    st.markdown("**What**: Captures exact timestamp the gate was satisfied.\n**Input**: `alert_ts`, `satisfied_at`\n**Output**: Causal UI Timeline\n**Module**: UI Layer\n**PS04**: Proves system isn't cheating with future data.")
