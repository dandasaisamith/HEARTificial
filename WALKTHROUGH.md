# TRACE-FX: Complete System Walkthrough

This document serves as a complete, step-by-step walkthrough of the TRACE-FX project. It details the journey from an empty codebase to a fully functional, deterministic financial-fraud intelligence system, explaining the core architecture and providing full file-by-file summaries.

## 1. How to Run on Windows (No `make` required)

Since Windows PowerShell does not ship with `make` by default, here are the direct Python commands that accomplish exactly what the `Makefile` does:

**Setup & Install:**
```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .
pip install -r requirements.txt
```

**Generate Synthetic Data:**
```powershell
# Generates seedA.csv, seedB.csv, seedC.csv, and demo_small.csv in data/
python -m tracefx data
```

**Run Tests:**
```powershell
pytest tests/
```

**Run the Evaluation Engine:**
```powershell
# Runs the pipeline over all data seeds and generates reports/eval_results.csv
python -m tracefx eval --data-dir data --out reports
```

**Launch the Interactive UI Demo:**
```powershell
python -m streamlit run app/app.py
```

---

## 2. Full System Architecture

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
                      Result
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
    Streamlit           CLI              Replay
       │                 │                 │
    Judge UI      Terminal Output    Self-contained HTML
```

---

## 3. The Build Journey (From Empty to Production)

TRACE-FX was built under a strict 6-hour autonomous build directive, forcing a highly pragmatic, deterministic, and pure-function approach.

### Phase 1: Foundation & Contracts
We began by defining the frozen types, documentation constraints, and configuration system:
- **Contracts**: Locked down architecture in `ARCHITECTURE_LOCK.md` and defined the exact shape of `Result`, `Evidence`, `Decision`, `LedgerLine`, and `Group` in `types.py`.
- **Config**: Locked down all arbitrary weights, thresholds, and caps into a unified configuration file (`config.yaml`).
- **Ingestion**: Built the data ingestion layer (`schema.py`) to aggressively parse CSVs, map columns, handle missing data, and safely convert timestamps to nanoseconds.

### Phase 2: Behaviors & Graphs
Before accusing anyone of fraud, we need to understand normal behavior and connections:
- **Behavior**: Calculated velocity, deviations, and standard behavior using an Isolation Forest to yield a score between `0..1` (`features.py` & `baseline.py`). Behavior alone never triggers fraud.
- **Networks**: Constructed a `networkx.MultiGraph` (`graph.py`). Implemented **Hub Caps**: if a Wi-Fi IP or device connects to more than 8 accounts, it's considered "Shared Infrastructure" and dropped, preventing a public library from being labeled a fraud ring.

### Phase 3: The Fraud Motifs (Structural Detectors)
We built 5 explicit fraud detectors (`motifs.py`). Instead of black-box ML, these look for structural realities in the data:
1. **M1 (Shared Device)**: Multiple accounts using the same device with no prior legitimate history.
2. **M2 (Common Sink)**: Many distinct payers sending money to one specific wallet within 24h.
3. **M3 (Pass-Through)**: Money received is rapidly forwarded (>=80%) to another account within 30 minutes.
4. **M4 (Sequence Cohort)**: Coordinated transaction sequences converging on sinks.
5. **M5 (Burst)**: Highly anomalous transaction bursts breaking an account's normal z-score baseline.

### Phase 4: The Ledger & The Gate
- **The Ledger** (`ledger.py`): Generates a balance sheet for every account. It adds positive points for Motifs (e.g., +30 for M2) and subtracts points for Exculpatory Evidence (e.g., -15 for old accounts, -20 for repeat legitimate payees).
- **The Gate** (`gate.py`): The deterministic judge. For an account to be marked `FRAUD`, it requires `net_points >= 60` AND at least 2 independent structural evidence types.

### Phase 5: Pipeline Orchestration & Simulator
- **Orchestration**: Wrapped the entire flow inside a safe executor (`pipeline.py`). If a motif crashes, it degrades gracefully and still generates a result.
- **Simulation**: Built a comprehensive generator (`simulate.py`) to create realistic synthetic banking data that mathematically forces fraud rings (to test recall).

### Phase 6: Reporting & The UI
- **Explanation**: Transformed computed ledger points into deterministic, natural-language explanations and recommended actions (`explain.py` & `actions.py`).
- **UI**: Created a Streamlit interface (`app.py`) featuring an aggressive dark mode, dynamic metrics, and an interactive account queue. Constructed causal `vis-network` HTML graphs (`replay_html.py`) to visually explain the fraud rings.

---

## 4. Comprehensive File Summaries

Below is a complete index and summary of every file within the TRACE-FX repository tree:

### 4.1. Root Directory
- **`Makefile`**: Automation shortcuts for Mac/Linux environments (setup, test, run).
- **`pyproject.toml`**: Python build system configuration (uses `setuptools.build_meta`).
- **`requirements.txt` / `requirements.lock.txt`**: Production and locked dependencies to guarantee deterministic builds across environments.
- **`config.yaml`**: The frozen configuration matrix containing point thresholds, feature window sizes, anomaly thresholds, and hub caps.
- **`audit.py`**: A comprehensive compliance checking script to verify determinism, causality, latency, and correctness across all phases of the pipeline.
- **`WALKTHROUGH.md`**: This document! Contains the architecture and file-by-file explanations.
- **`README.md`**: Top-level overview and run instructions for the repository.
- **`AGENTS.md` / `GEMINI.md` / `SCOPE.md` / `DISCLOSURE.md` / `sai.md` / `CLAUDE.md`**: Guardrails, system prompts, operational scope, and role instructions for autonomous AI agents interacting with the repository.
- **`.gitignore`**: Files and directories to ignore in git.

### 4.2. `docs/` - System Documentation & Specifications
- **`ARCHITECTURE_LOCK.md`**: The supreme source of truth for the system's design. All implementation must adhere strictly to this lock file.
- **`ARCHITECTURE.md`**: High-level module boundary definition and structural guidance.
- **`SYSTEM_DESIGN.md`**: Comprehensive architectural vision, design principles, and constraint documentation.
- **`DATA_SPEC.md`**: Strict specification of the input schema, data formats, types, and constraints expected by the pipeline.
- **`CONTRACTS.md`**: Describes the immutable boundaries and data shapes between modules.
- **`GUARDRAILS.md`**: Rules governing data writing and UI updates to prevent corruption of the pure engine.
- **`TASKS.md`**: The sequence of autonomous build tasks, their priorities, and completion states.
- **`FOUNDATION_AUDIT.md`**: Log of the initial pre-build codebase inspection.
- **`AUDIT_BASELINE.md`**: The final post-build audit report verifying that all C1-C9 system requirements and determinism checks pass.
- **`DECISIONS_LOG.md`**: A running ledger of technical and architectural decisions made when resolving ambiguities.
- **`BLUEPRINT.md`**: Historical and superseded reference material (must not override the LOCK file).
- **`DEMO.md`**: Script and expectations for the final UI demonstration.

### 4.3. `src/tracefx/` - Core Pipeline Engine
- **`__init__.py`**: Exposes the package.
- **`__main__.py`**: Allows running the module via `python -m tracefx`.
- **`types.py`**: The fundamental, immutable dataclasses representing domain objects (`Result`, `Evidence`, `Decision`, `LedgerLine`, `Group`).
- **`config.py`**: Parses and validates `config.yaml`, injecting thresholds natively into Python objects.
- **`schema.py`**: The ingestion gateway. Normalizes CSV columns, filters missing data, and casts timestamps safely to UTC nanoseconds (`int64`). Performs capability detection.
- **`features.py`**: Computes time-windowed aggregates (1h/24h velocity), standard deviations, and relative behaviors (amount percentiles, new entity interactions).
- **`baseline.py`**: Fits a scikit-learn `IsolationForest` on the engineered features to yield a `0..1` behavioral anomaly score. Also generates behavior-based evidence.
- **`graph.py`**: Constructs a typed `networkx.MultiGraph` linking accounts to devices, IPs, merchants. Enforces "Hub Caps" (e.g., dropping IPs with >8 accounts to prevent hostel Wi-Fis from being flagged as fraud rings).
- **`motifs.py`**: Contains the 5 strictly structural fraud detectors (`M1_shared_device`, `M2_common_sink`, `M3_pass_through`, `M4_sequence_cohort`, `M5_burst`).
- **`ledger.py`**: The central brain. Takes motif detections and behavioral signals, allocates positive points for anomalies, and applies negative points (exculpatory logic) for things like long tenure or repeat legitimate payees.
- **`gate.py`**: The deterministic judge. Enforces the strict rule that FRAUD requires both a high point threshold (`>=60`) AND at least two independent structural motifs. Handles REVIEW and LEGIT fallbacks.
- **`rollup.py`**: Aggregates individual account decisions into broader `Group` decisions by finding connected components purely over *evidence links* (not raw connectivity).
- **`explain.py`**: Translates ledger logic and point math into deterministic, human-readable explanations.
- **`actions.py`**: Maps specific final decisions and motif configurations to recommended operational actions (e.g., "Hold funds", "Step-up auth").
- **`pipeline.py`**: Orchestrates the entire pipeline, flowing data from `schema.py` down to `Result`, wrapping steps in safe fallbacks to ensure fail-soft capability.
- **`simulate.py`**: Massive data generation engine capable of crafting deeply realistic, complex synthetic transactional datasets, explicitly injecting mathematically sound fraud rings and legitimate behavior for evaluation.
- **`evaluate.py`**: Measures the pipeline against ground truth data (truth JSONs), calculating PR-AUC, Precision, and Recall across various synthetic seeds.
- **`casefile.py`**: Generates a self-contained HTML/Markdown report artifact using Jinja2 templates, detailing all findings for a given run.
- **`replay_html.py`**: Constructs causal, interactive visualizations using `vis-network`, producing self-contained HTML files plotting the detected fraud graphs.
- **`cli.py`**: Provides the command-line interface (`tracefx score`, `tracefx eval`, `tracefx data`) utilizing `argparse`.

### 4.4. `app/` - User Interface
- **`app.py`**: The Streamlit dashboard. A dark-themed, dynamic UI featuring real-time metrics, an interactive account queue, split-view layout for evidence ledgers, and embedded HTML visualizations.
- **`assets/`**: Vendored assets, specifically local copies of `vis-network` to prevent external CDN dependencies in the offline deployment.

### 4.5. `tests/` - Quality Assurance
Contains a complete `pytest` suite ensuring 100% deterministic reliability.
- **`test_config.py`**: Asserts configuration integrity.
- **`test_contracts.py`**: Enforces strict API boundaries on the types.
- **`test_gate.py`**: Validates the point threshold math and structural requirements.
- **`test_motifs.py`**: End-to-end unit tests on individual structural detectors.
- **`test_pipeline.py`**: Tests the entire E2E data flow, including graceful degradation on failure.
- **`test_schema.py`**: Ensures exact data casting and nanosecond translation accuracy.

### 4.6. `data/` and `reports/` - Data Storage
- **`data/`**: Stores the generated CSV files (`seedA.csv`, `seedB.csv`, `seedC.csv`, `demo_small.csv`) and their corresponding ground truth JSONs.
- **`reports/`**: The output directory for evaluation metrics (`eval_results.csv`) and generated case file reports.


<!-- BASELINE:START -->
<!-- BASELINE:END -->

<!-- EXTERNAL:START -->
<!-- EXTERNAL:END -->
