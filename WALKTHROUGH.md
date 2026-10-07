# TRACE-FX: Complete System Walkthrough & Architectural Evolution

This document serves as a complete, step-by-step walkthrough of the TRACE-FX project, including the fundamental engine build-out and the subsequent major Streamlit UI/UX architectural overhaul (PS04 HacKnex proof mode). It details the journey from an empty codebase to a fully functional, deterministic financial-fraud intelligence system, explaining every major design decision.

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

### Phase 5: The UI Architectural Rescue & Redesign
The original Streamlit application was technically populated but failed as a product—navigation was poor, investigation flows were unclear, and it felt like generic AI dashboarding. We executed a ground-up product rescue to turn it into a true "Financial Investigation Console".

**Key Changes:**
- **`st.navigation` Multi-page Routing**: Converted the single `app.py` script into a scalable multi-page app with `01_mission_control.py`, `02_scorecard.py`, `03_case_queue.py`, `04_fraud_rings.py`, `05_replay.py`, and `06_how_it_works.py`.
- **`engine_api.py` Event Wrapper**: Separated the engine from the UI. We wrapped `pipeline.run` utilizing Python's `unittest.mock.patch` on `pipeline._safe` to emit real-time event updates to the UI, proving to judges that the system performs live schema parsing, feature engineering, graph building, and gate logic *without modifying the core pipeline code*.
- **Live Scorecard & Strict Evaluation**: Integrated `tracefx.evaluate` directly into the UI to present un-gamed metrics (Precision, Recall, PR-AUC).
- **Plotly Fraud Rings**: Replaced static generic views with interactive `NetworkX` -> `Plotly` graphs showing the exact topologies of M1-M5 rings.
- **Causal Temporal Replay**: Rebuilt the replay tab leveraging Streamlit 1.37+ `st.fragment(run_every=...)` to advance the timeline state, explicitly showing when evidence was acquired and when the Precision Gate finally tipped to `FRAUD`.
- **"Why Not Fraud?" Counterfactuals**: Designed a UI block that proves the engine avoids false positives on legitimate high-value transactions by showing missing structural evidence or applied exculpatory points.

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
│   ├── graph.py                          # MultiGraph & Hub Caps
│   ├── motifs.py                         # M1-M5 structural detectors
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
│       ├── 02_scorecard.py               # Evaluation metrics
│       ├── 03_case_queue.py              # Ledger & Precision Gate breakdown
│       ├── 04_fraud_rings.py             # Plotly NetworkX topologies
│       ├── 05_replay.py                  # Causal st.fragment timeline
│       └── 06_how_it_works.py            # Live PS04 proof matrix
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

**2. Prewarm the Engine Cache (Optional):**
```powershell
python scripts/prewarm.py
```

**3. Launch the Investigation Console:**
```powershell
python -m streamlit run app/app.py
```
*Navigate to `Mission Control`, select `demo_small.csv`, and execute the pipeline to observe the real-time event feed. Then proceed through the `Scorecard`, `Case Queue`, and `Fraud Rings` pages to verify the PS04 compliance matrix.*
