# TRACE-FX: Complete System Walkthrough & Architectural Evolution

This document serves as a complete, step-by-step walkthrough of the TRACE-FX project, including the fundamental engine build-out and the subsequent major Streamlit UI/UX architectural overhauls (PS04 HacKnex proof mode + Final Forensic Redesign). It details the journey from an empty codebase to a fully functional, highly optimized, deterministic financial-fraud intelligence system, explaining every major design decision.

## 1. Core Architecture & Philosophy

The central proposition of TRACE-FX is: **"Don't just detect the fraud. Show the evidence, and show why we didn't accuse the innocent."**

The engine operates via a strictly causal, deterministic pipeline without relying on black-box ML classification for the final decision. The full architecture flow is:

```text
                         config.yaml
                              │
                              ▼
CSV ───────────────► schema.py (Parsing & Clean up)
                         │
                         ├──────────────► capabilities/quality
                         │
                         ▼
                    features.py (Velocity, Deviations)
                         │
                         ▼
                    baseline.py (Behavioral Scoring 0..1)
                         │
                         ▼
                    graph.py (Typed Entity Graph & Hub Caps)
                         │
                         ▼
                    motifs.py (Structural Detectors M1-M5)
                 ┌───────┼────────┐
                 │       │        │
                M1      M2       M3
                M4      M5
                 │       │        │
                 └───────┼────────┘
                         ▼
                    Evidence[]
                         │
                         ▼
                    ledger.py (Point allocation & Exculpatory logic)
                         │
                         ▼
                     gate.py (Threshold & Validation)
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
           FRAUD       REVIEW       LEGIT
             │           │           │
             └───────────┼───────────┘
                         ▼
                    rollup.py (Account & Group formulation)
                         │
                         ▼
              explain.py + actions.py (Explanations & Next steps)
                         │
                         ▼
                      Result (Immutable Data Contract)
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
    engine_api          CLI              Replay
       │                                   │
   Streamlit UI                         HTML Reports
```

## 2. The Build Journey: From Engine to Investigation Console

TRACE-FX was built under strict operational constraints.

### Phase 1: Engine Foundation & Contracts
We began by defining the frozen types, documentation constraints, and configuration system:
- **Contracts**: Locked down architecture in `ARCHITECTURE_LOCK.md` and defined the exact shape of `Result`, `Evidence`, `Decision`, `LedgerLine`, and `Group` in `types.py`.
- **Config**: Locked down all arbitrary weights, thresholds, and caps into a unified configuration file (`config.yaml`).

### Phase 2: Behaviors & Graphs
Before accusing anyone of fraud, we need to understand normal behavior and connections:
- **Behavior**: Calculated velocity, deviations, and standard behavior using an Isolation Forest to yield a score between `0..1` (`features.py` & `baseline.py`). Behavior alone never triggers fraud.
- **Networks**: Constructed a `networkx.MultiGraph` (`graph.py`). Implemented **Hub Caps**: if a Wi-Fi IP connects to more than 8 accounts, it's considered "Shared Infrastructure" and dropped, preventing public networks from being labeled a fraud ring.

### Phase 3: Structural Fraud Motifs (M1-M5)
We built 5 explicit fraud detectors (`motifs.py`). Instead of black-box ML, these look for structural realities:
1. **M1 (Shared Device)**: Multiple accounts using the same device with no prior legitimate history.
2. **M2 (Common Sink)**: Many distinct payers sending money to one specific wallet within 24h.
3. **M3 (Pass-Through)**: Money received is rapidly forwarded (>=80%) to another account.
4. **M4 (Sequence Cohort)**: Coordinated transaction sequences converging on sinks.
5. **M5 (Burst)**: Highly anomalous transaction bursts.

### Phase 4: The Ledger & Precision Gate
- **The Ledger** (`ledger.py`): Generates a balance sheet for every account. Adds positive points for Motifs (e.g., +30 for M2) and subtracts points for Exculpatory Evidence (e.g., -15 for old accounts).
- **The Gate** (`gate.py`): The deterministic judge. For an account to be marked `FRAUD`, it requires `net_points >= 60` AND at least 2 independent structural evidence types.

### Phase 5: The Forensic UI Rescue & Vectorization
The original Streamlit application was technically populated but failed as a product. We executed a ground-up product rescue to turn it into a true "Financial Investigation Console" and optimized the backend for production workloads.

**Backend Vectorization:**
- **O(1) Checksets:** Eliminated repeated `O(n)` boolean mask scans across the dataset by pre-computing static sets of `(payer, payee)` pairs, slashing `graph.py` and `M1` motif execution times.
- **Vectorized Lookups:** Replaced `pandas.iterrows()` loops with memory-contiguous `zip()` aggregations on DataFrame columns.

**UI Restructuring (`st.navigation`):**
- **01 Mission Control**: Live `S1-S9` engine orchestration with pipeline phase observability.
- **02 Detection Quality**: Robust metrics (PR-AUC, Recall) adapting dynamically to the presence/absence of ground truth in hybrid/real datasets.
- **03 Investigate**: Forensic drill-down. Shows exact Isolation Forest behavioral logic, Ledger balance sheets, active Precision Gate math, and the PS04 "Why Not Fraud?" counterfactual breakdown.
- **04 Fraud Networks**: Semantic `Plotly` ring topology rendering.
- **05 Temporal Replay**: Causal time-stepper locked explicitly to `satisfied_at` and `alert_ts` thresholds.
- **06 How TRACE-FX Works**: Interactive architecture explorer and live PS04 Live Proof matrix.
- **07 Data & System**: Live registry scanner tracking `data/Traindata/` (raw external mappings) and local capabilities.

## 3. Full Codebase Directory Tree

```text
TRACE-FX/
├── data/                                 # Datasets (demo_small.csv, seeds, etc.)
│   └── Traindata/                        # External/Raw Kaggle datasets
├── config.yaml                           # System weights and thresholds
├── docs/                                 # Documentation & Spec Locks
│   ├── ARCHITECTURE_LOCK.md              
│   ├── DATA_SPEC.md                      
│   ├── UI_CHECK.md                       # UI functional validation matrix
│   └── ...
├── src/tracefx/                          # Core Engine
│   ├── types.py                          # Immutable data contracts
│   ├── config.py                         # Config parsing
│   ├── schema.py                         # Data ingestion & UTC normalization
│   ├── features.py                       # Rolling behavioral windows
│   ├── baseline.py                       # IsolationForest anomaly scoring
│   ├── graph.py                          # MultiGraph & Hub Caps (Vectorized)
│   ├── motifs.py                         # M1-M5 structural detectors (Vectorized)
│   ├── ledger.py                         # Evidence point allocation
│   ├── gate.py                           # FRAUD/REVIEW logic
│   ├── rollup.py                         # Connected components & groups
│   ├── explain.py                        # NLP explanation generator
│   ├── pipeline.py                       # Orchestration & safe wrappers
│   ├── evaluate.py                       # Honest metrics calculator
│   └── engine_api.py                     # Streaming wrapper for live UI updates
├── app/                                  # Streamlit UI
│   ├── app.py                            # Entrypoint & Router
│   ├── ui/
│   │   ├── theme.py                      # Global Dark SOC Theme injected via CSS
│   │   └── datasets.py                   # Automatic dataset discovery scanner
│   └── pages/                            # Navigable UI views
│       ├── 01_mission_control.py         # Live pipeline execution 
│       ├── 02_detection_quality.py       # Strict / Any-Ring evaluation metrics
│       ├── 03_investigate.py             # Ledger, Gate, & False-Positive forensic view
│       ├── 04_fraud_networks.py          # Plotly NetworkX topologies
│       ├── 05_temporal_replay.py         # Causal st.fragment timeline
│       ├── 06_how_tracefx_works.py       # Live PS04 proof matrix
│       └── 07_data_and_system.py         # Dataset scanner & real-world mapping status
├── tests/                                # 100% deterministic test suite
│   └── test_*.py
├── requirements.txt                      # Pinned dependencies (streamlit, plotly, etc.)
└── WALKTHROUGH.md                        # This document
```

## 4. How to Execute & Verify the System

**1. Run the Determinism & Unit Tests:**
```powershell
python -m pytest -q tests
```
*Ensures that core engine logic (types, gates, motifs) has not regressed and scores remain perfectly deterministic.*

**2. Launch the Investigation Console:**
```powershell
python -m streamlit run app/app.py
```
*Navigate to `Mission Control`, select `demo_small.csv`, and execute the pipeline to observe the real-time event feed. Then proceed through the `Investigate` and `Fraud Networks` pages to verify the PS04 compliance matrix.*
