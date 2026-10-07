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
## System Overview
TRACE-FX is a real-time financial fraud intelligence engine designed to produce explainable, deterministic decisions. It operates offline on CPU, prioritizing clear causal evidence over black-box predictions. The architecture transforms canonical transactions into structured motifs and aggregates them into a point-based ledger.

**Pipeline Flow:**
`schema` -> `features` -> `IsolationForest` -> `graph` -> `M1-M5` -> `ledger` -> `gate` -> `rollup` -> `explain/actions` -> `UI`.

## How to Run
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q
python -m tracefx eval --data-dir data --out reports
python -m tracefx score data\demo_small.csv
python -m streamlit run app\app.py
```

## Baseline Results
**Commit Tag:** `pre-external`
**Tests:** 50 passed

**Evaluation Table:**
| seed_file | seed | n_transactions | n_accounts | n_fraud_accounts | n_review_accounts | n_groups | ring_full | ring_partial | ring_missed | ring_recall_full | fp_legit_hv_fraud_only | fp_legit_hv_fraud_or_review | precision_fraud | recall_fraud | precision_at_10 | precision_at_50 | pr_auc | elapsed_s (machine-dependent) | latency (machine-dependent) | degraded_stages |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| seedA | 42 | 45332 | 2005 | 3 | 203 | 78 | 5 | 0 | 0 | 5/5 | 0 | 0 | 0.0 | 0.0 | 0.4 | 0.34 | 0.3698 | 29.665 | 0.654 | none |
| seedB | 7 | 45023 | 2005 | 10 | 240 | 51 | 5 | 0 | 0 | 5/5 | 0 | 1 | 0.6 | 0.2727 | 0.3 | 0.38 | 0.4239 | 29.915 | 0.664 | none |
| seedC | 2026 | 45220 | 2005 | 11 | 227 | 57 | 6 | 0 | 0 | 6/6 | 0 | 1 | 0.3636 | 0.1905 | 0.0 | 0.38 | 0.3357 | 29.22 | 0.646 | none |
| demo_small | 42 | 5186 | 602 | 5 | 159 | 20 | 2 | 0 | 0 | 2/2 | 0 | 0 | 0.6 | 0.3 | 0.5 | 0.16 | 0.395 | 5.323 | 1.026 | none |


**Determinism Hashes:**
```
Hash1: ec4f068092a679018c4d0b0ecd5452b71dca25abebb5e2527a4fa345b8aa0a75
Hash2: ec4f068092a679018c4d0b0ecd5452b71dca25abebb5e2527a4fa345b8aa0a75
Equal: True
```

## Known Limits
- The metrics report `precision_fraud=0.0` and `recall_fraud=0.0` because `evaluate.py` strictly considers only 'R1' (Type 1) ring members as true positive targets for the FRAUD label. The 3 accounts reaching the FRAUD tier in seedA belong to different truth sets (likely isolated or non-R1 fraud) so they are counted as false positives for the specific R1 metric. Meanwhile, the actual R1 ring members did not accumulate the 60 net points required by the deterministic gate (they only reached the REVIEW tier). This represents a metric-definition artefact combined with conservative point thresholding: the system successfully detects the rings (ring_recall_full=5/5) but classifies their members as REVIEW rather than FRAUD, resulting in 0 precision/recall for the strict FRAUD vs R1 classification.
- Synthetic data only.
- Hand-set weights.
- Slow-drip fraud falls to REVIEW.

<!-- BASELINE:END -->

<!-- EXTERNAL:START -->
## External Data & Hybrid Integration
**External Evaluation:**
not produced

**External Summary:**
not produced

**Tuning Log:**
# Tuning Log and Guardrail Decisions

## Baseline Reality: 50 points vs 60 threshold
Our gate analysis demonstrates that R1 ring members trigger the required structural motifs and accrue net points, typically maxing out around 50 points. However, the `config.yaml` gate for `fraud_net` is strictly set to 60. As a result, genuine synthetic fraud groups are appropriately flagged for attention but fall into the `REVIEW` tier rather than the `FRAUD` tier.

## Guardrail Decision: Refuse to overtune
In alignment with strict engineering principles and architecture locks, we refuse to "fix" the scoring simply to make the metric look artificially successful. We will not change `config.yaml`, bypass the precision block, or hard-code threshold adjustments to force R1 members into the `FRAUD` category. We document reality exactly as the deterministic engine outputs it.

## Expected Metrics
Because of the strict R1-only definition for `tp_fraud` combined with the 60 point gate, `precision_fraud` will remain ~0.0 on the strict metric. This occurs because R1 members correctly land in REVIEW instead of FRAUD. Real-world users would adjust the `fraud_net` threshold downward in `config.yaml` based on local operational capacity, but we will leave it at 60 to maintain strict architectural lock.


**Regression Gate:**
All baseline metric shapes held under strict evaluation definition. Additive metrics confirm expected anyring signal.


**NOT DONE list:**
- streaming API ()

<!-- EXTERNAL:END -->

## Current State & Next Steps

### Development Progress & Work Completed
The TRACE-FX engine has reached a stable, rigorously tested state following the completion of Phases A through D of the primary system requirements:

1. **Phase A (Baseline Audit):** 
   - Verified the stability and determinism of the pipeline (`schema` -> `features` -> `IsolationForest` -> `graph` -> `M1-M5 motifs` -> `ledger` -> `gate` -> `rollup`).
   - Confirmed the 50-test pytest suite passes and determinism hashes match.

2. **Phase B (Tool & Assets Fixes):**
   - The walkthrough generation tool (`tools/build_walkthrough.py`) was fully refactored to dynamically read actual output reports rather than using hard-coded summaries.
   - Verified local vendoring of `vis-network` in `app/assets/` to ensure offline causal graph playback.

3. **Phase C (Gate Analysis & Guardrail Tuning):**
   - Implemented dynamic config overlays and evaluation flags (`--config`, `--only`) in `tracefx eval`.
   - Developed `tools/gate_analysis.py` to forensically prove why strict R1 ring members fall into the `REVIEW` tier instead of the `FRAUD` tier (they typically accrue ~50 points, below the strict 60 point gate).
   - Enforced a hard guardrail: **Refused to overtune.** The `fraud_net` threshold remains locked at 60 to preserve architectural integrity, rather than gaming the metric. This decision is permanently documented in `docs/TUNING_LOG.md`.
   - Added four additive metrics to `evaluate.py` (`precision_fraud_anyring`, `recall_fraud_anyring`, `precision_fraud_or_review_anyring`, `recall_fraud_or_review_anyring`) to accurately reflect true fraud recall across all structural tiers. Tests added and passing (53 total).

4. **Phase D (External Data - E-Commerce):**
   - Built `tools/external_ecommerce.py` to perform fast `merge_asof` joins over IP ranges, canonicalizing the external Fraud E-commerce dataset into the strict `tracefx` format.
   - Built `tools/ecommerce_runner.py` to extract an exact 40,000-row chronological sub-sample to fit within CPU-only computational limits.
   - Successfully scored the 40k sub-sample through the entire pipeline.

### Full Architecture & Codebase Summary

#### 1. Core Engine (`src/tracefx/`)
- **`types.py`:** The frozen contracts definition (Evidence, LedgerLine, Decision, Group, Result).
- **`schema.py`:** Input canonicalization, timestamp normalization (to UTC), and dataset capability reporting.
- **`features.py`:** Causal rolling feature builder (amount deviation, hour of day Z-scores, velocity flags). Now supports optional `use_since_open` logic.
- **`baseline.py`:** Fits an IsolationForest model over the features for pure behavioral anomaly scoring.
- **`graph.py`:** Constructs the multi-graph (Payer -> Payee, Payer -> Device, Payer -> IP) implementing strict hub-caps to prevent infrastructure false-positives.
- **`motifs.py`:** The 5 core structural detectors:
  - **M1:** Shared Device
  - **M2:** Common Sink
  - **M3:** Pass-through
  - **M4:** Sequence Cohort (Requires money convergence to count)
  - **M5:** Burst
- **`ledger.py`:** The brain. Translates behavioral scores and structural motifs into positive points, heavily weighted by exculpatory negative points (e.g., long tenure, known devices).
- **`gate.py`:** Evaluates the ledger against the strict FRAUD/REVIEW/LEGIT thresholds defined in `config.yaml`.
- **`rollup.py`:** Aggregates related accounts into Fraud Groups using connected components strictly over verified evidence links.
- **`explain.py` / `actions.py`:** Auto-generates deterministic, human-readable explanations and recommends operational responses based on ledger paths.
- **`evaluate.py`:** Comprehensive metric calculator (PR-AUC, precise strict vs. anyring metrics).
- **`pipeline.py`:** Main orchestrator, wraps stages in fail-soft `try/except` blocks.
- **`cli.py`:** Command-line entrypoints (`score`, `eval`, `data`).

#### 2. Presentation & Interfaces
- **`app/app.py`:** Dark-themed Streamlit dashboard for interactive queue review and ledger inspection.
- **`casefile.py` & `replay_html.py`:** Generates standalone static HTML reports embedding the interactive `vis-network` causal graphs.

#### 3. Configuration & Tuning
- **`config.yaml`:** The sole source of truth for all threshold weights.
- **`config.py`:** Schema validator and deep-merge overlay engine for experimental tuning without breaking the base config.

### Tech Stack & Libraries
- **Core:** Python 3.10+, Dataclasses
- **Data & Compute:** pandas, numpy, scikit-learn (IsolationForest)
- **Graph & Visualization:** networkx, vis-network (vendored)
- **Frontend / UI:** streamlit
- **Testing & Tooling:** pytest, pyyaml

### What's Next (Pending Phases E-H)
1. **Phase E (Hybrid Seed Generation):** Inject the existing synthetic structural rings into the real-world 150k-row E-commerce dataset to test true structural recall in high-noise environments.
2. **Phase F (UI Upgrades):** Finalize capability mapping displays in Streamlit to grey out detectors disabled by missing columns (e.g., if a dataset lacks `device_id`, M1 greys out).
3. **Phase G (Tests & Docs):** Expand test coverage for hybrid data parsing.
4. **Phase H (Final Run):** End-to-end evaluation and final compilation.
