> SUPERSEDED REFERENCE. Where this differs from ARCHITECTURE_LOCK.md, DATA_SPEC.md, CONTRACTS.md or TASKS.md v3, those win (e.g. no pyvis, no 40-frame replay, tx_type column, parallel lanes). Agents: ignore this file for decisions.

# TRACE-FX — MASTER BLUEPRINT (root context for HNX26PSI04)

Paste this whole file into your AI coding tool as the project context. It overrides any default suggestion the AI makes.

---

## 0. DECISIONS LOCKED (no ambiguity)

| Item | Decision |
|---|---|
| Problem | HNX26PSI04 Real-Time Financial Fraud Intelligence |
| Name / pitch | **TRACE-FX** — "Don't just detect the fraud. Show the evidence, and show why we didn't accuse the innocent." |
| Core idea | Behavioural scorer + typed entity graph + 5 fraud motifs → **evidence ledger** → **precision gate** → FRAUD / REVIEW / LEGIT |
| ML | IsolationForest (unsupervised). LightGBM only if labels exist (Level 3). **No GNN, no conformal, no LLM in decisions** |
| Data | Own deterministic simulator (3 seeds). IEEE-CIS adapter = stretch only |
| Stack | Python 3.10+, pandas, numpy, scikit-learn, networkx, pyvis, streamlit, jinja2, pytest. (lightgbm, fastapi optional) |
| GPU | Not used. CPU only. The 4060 is irrelevant |
| Build window | Tonight prep, tomorrow 10:00–15:00 |
| Output contract | One function: `pipeline.run(df, cfg) -> Result`. Everything (UI, CLI, tests) consumes it |
| "Real-time" claim | Batch scoring + timeline replay with per-transaction latency shown. Streaming engine is Level 3; do not claim true streaming unless built |

---

## 1. ADD-ONS BEYOND THE PROBLEM STATEMENT

The statement asks for: tx risk, account risk, suspicious groups, pattern, diagram, action. These add-ons are extras, ranked by attraction / speed / cost.

| # | Add-on | What the judge sees | Why it helps | Cost | Tier |
|---|---|---|---|---|---|
| A1 | **Lead-time replay** | Ring assembles on a timeline; alert fires; "detected N transactions before cash-out, ₹X intercepted" | Makes "real-time" visible; the dopamine moment | M | SHOULD |
| A2 | **Why-not-fraud panel** | Green shield on legit high-value: tenure, repeat payee, known device | Direct hit on "avoid flagging legit high-value" | L | **MUST** |
| A3 | **Case File export** | One-click printable HTML/PDF case report (accounts, evidence, timeline, action) in suspicious-transaction-report style | Industry judges love workflow closure; also your "sample output" | L | SHOULD |
| A4 | **Judge's pen** | Judge edits a transaction, ledger recomputes live | Proves nothing is hard-coded | M | SHOULD |
| A5 | **Red-team button** | Fraudsters change devices/timing; shows which evidence survives | Covers the "accounts change behaviour" advanced item | M | NICE |
| A6 | **Sleeper/drift flag** | "Dormant 90 days, then burst" or behaviour shift via EWMA | Cheap advanced-item coverage | L | NICE |
| A7 | **Source-row re-verify** | Click a ledger line → raw CSV rows highlighted | Trust, auditability | L | SHOULD |
| A8 | **Latency HUD + headless CLI** | Live p50/p95 ms per tx; `python -m tracefx score in.csv` | Fast results, and works if judges give their own file | L | SHOULD |
| A9 | **Action simulator** | "If we freeze payee W3: 7 pending transfers blocked, ₹4.2L saved" | Closes the loop on "what action to take" | L | NICE |
| A10 | **Data-quality report on upload** | Missing columns, duplicates, mapping — then graceful degrade | Robustness for unknown judge data | L | SHOULD |
| A11 | **Precision-budget dial** | Slider: FP budget → alerts / precision / recall | Turns the FP cap into a feature | L | NICE |
| A12 | Streaming engine + FastAPI `/score` | True per-transaction ingest | Strongest "real-time" proof, but riskiest | H | STRETCH |

Efficiency tricks (speed of results, no extra features): vectorised pandas groupby; inverted indexes for device→accounts and payee→payers; n-gram inverted index for sequences (O(N), no pairwise compare); cache the demo run to parquet/JSON; precompute replay frames; demo dataset ~5k tx (live), evaluation datasets ~50k tx.

---

## 2. SOFTWARE PRINCIPLES (the rules the code obeys)

1. **One contract.** UI, CLI, tests depend only on `Result`. Never on internals.
2. **Pure functions.** Each stage: DataFrame in → DataFrame/dataclass out. No globals.
3. **Fail-soft stages.** Each stage wrapped; on error, log, set `degraded=True`, continue with the earlier level.
4. **Config over constants.** All weights/thresholds in `config.yaml`; nothing magic in code.
5. **Determinism.** Seeds everywhere; same input → same output.
6. **Single code path.** Demo, CLI and tests all call `pipeline.run`.
7. **Small modules, typed.** Dataclasses and type hints; one responsibility per file.
8. **Tests are the spec.** Each motif and each hard negative has a test before the UI.
9. **Cut lines.** Every feature has a flag that turns it off without breaking others.
10. **Honest numbers.** Metrics printed only from real runs.

---

## 3. ARCHITECTURE

```
            ┌───────── config.yaml ─────────┐
CSV ─► schema.py ─► features.py ─► baseline.py ─┐
 (map/validate/    (account baselines,           │ behaviour score 0–1
  quality report)   peer percentile, drift)      ▼
                  graph.py (typed edges, hub caps) ─► motifs.py (M1–M5 → Evidence[])
                                                        ▼
                         ledger.py (+evidence, −exculpatory) ─► gate.py
                                                        ▼
                     FRAUD / REVIEW / LEGIT per tx ─► rollup.py (account + group risk)
                                                        ▼
                  explain.py (templates) + actions.py ─► Result
                                                        ▼
          app.py (Streamlit)   cli.py   replay.py   casefile.py   evaluate.py
```

### 3.1 Data schema (canonical)
Required: `tx_id, ts, payer_id, payee_id, amount`.
Optional (features degrade if absent): `device_id, ip, merchant_id, item_id, channel, city, account_open_date, label`.
`schema.py` maps judge columns → canonical names, drops duplicates, parses timestamps, and returns a quality report.

### 3.2 Core types
```python
@dataclass(frozen=True)
class Evidence:   # one motif hit
    type: str           # "shared_device" | "common_sink" | "pass_through" | "sequence_cohort" | "burst"
    accounts: tuple; tx_ids: tuple; first_ts; last_ts; strength: float; detail: dict

@dataclass(frozen=True)
class LedgerLine:  # one scored reason
    source: str; points: float; text: str; tx_ids: tuple

@dataclass
class Decision:    # per transaction
    tx_id; label; net_points; risk: float; ledger: list[LedgerLine]; action: str

@dataclass
class Result:
    tx: DataFrame; accounts: DataFrame; groups: list[Group]; evidence: list[Evidence]
    decisions: dict[str, Decision]; graph: dict; metrics: dict; degraded: list[str]; quality: dict
```

### 3.3 Algorithms (starting parameters, tune on seed A, report on B/C)

- **Behaviour score:** features = amount z-score vs own history, amount percentile vs peer group (tenure/channel), velocity (1h/24h), new-payee rate, new-device flag, hour-of-day deviation. IsolationForest → percentile 0–1. Cold-start accounts: neutral prior, no behaviour points.
- **M1 shared_device:** device used by ≥2 accounts with no prior payer/payee link between them. If device degree > `DEG_CAP` (8) or IP degree > 8 → treat as public/shared, weight 0. Strength rises with number of accounts and low tenure.
- **M2 common_sink:** payee receiving from ≥4 distinct accounts within 24 h, unless payee has history of repeat/cadenced payers (landlord, school) → weight reduced.
- **M3 pass_through:** account receives then sends ≥80% of the amount within 30 min; chains of ≥2 hops count more.
- **M4 sequence_cohort:** per account, ordered item/merchant tokens in a window → 3-grams → weight each by IDF (rare = high) → inverted index → accounts sharing ≥2 rare 3-grams link up → cohorts of ≥4. **Counts only if the cohort also converges on a sink (M2) or pass-through (M3).** This is what blocks flash-sale false positives.
- **M5 burst:** account's 1h count vs own baseline z > 3, plus cohort start-times clustered within a short window.
- **Drift (A6):** EWMA of amount/velocity/new-payee rate; "sleeper" = ≥90 days dormant then burst.

**Ledger (starting weights, config):**
Positive: behaviour anomaly up to +20 · M1 +20 · M2 +30 · M3 +25 · M4 +25 · M5 +10 · sleeper +10.
Exculpatory: tenure > 365d −15 · payee seen ≥3 times before −20 · device used ≥5 times before −10 · amount ≤ account p95 −10 · within peer range −5.

**Gate:** FRAUD if net ≥ 60 **and** ≥ 2 independent structural evidence types (M1–M5; behaviour alone never counts). REVIEW if net ≥ 30 or one strong structural type. Else LEGIT. Weights are a transparent hand-set policy, not learned; say so.

**Rollup:** account risk = 1 − Π(1 − pᵢ) over its transaction risks (pᵢ = clip(net/100)). Group = connected components over evidence links only (never raw shared entities); group risk = max member risk, boosted by cohesion. Ring "family" label: star-mule / chain / cohort.

**Actions (deterministic):** FRAUD tx → hold + escalate; ring → freeze common payee, block shared device, notify members; REVIEW → step-up authentication / analyst queue; LEGIT → none.

**Replay (A1):** precompute `run(df[ts ≤ t])` at ~40 checkpoints for the demo set → store frames. Lead time = ring's outgoing ₹ after the first FRAUD-alert timestamp. Label every such number "simulated".

---

## 4. END-TO-END WORKFLOW

1. Upload CSV (or pick demo seed) → quality report + column mapping.
2. Features + behaviour score.
3. Build entity graph (typed edges, hub caps).
4. Run motifs → Evidence list.
5. Ledger + gate → per-transaction decision.
6. Roll up → account risk, group risk, ranked queue.
7. UI: ranked alerts → click → evidence chain + highlighted ring subgraph + why-not panel + recommended action.
8. Optional: replay timeline, judge's pen, red-team, case-file export.
9. Evaluate: metrics vs baseline on seeds A/B/C → printed report.

---

## 5. CROWDED vs OURS (technologies)

| Layer | Crowd default | Ours | Why |
|---|---|---|---|
| Model | GraphSAGE/GAT + XGBoost | IsolationForest + motifs | explainable, no training, fast |
| Explanation | SHAP bars | Evidence ledger + why-not | rubric asks for reasoning |
| Threshold | 0.5 | Validation-tuned gate | FP cap |
| Data | IEEE-CIS | Hard-negative simulator + unseen seeds | rings exist, leaks controlled |
| Graph | hairball | ring subgraph + 1 hop | legibility |
| Demo | static dashboard | replay + pen + red-team | memorable |
| Uncertainty | none / fake conformal | REVIEW tier | honest abstention |

---

## 6. REPOSITORY

```
tracefx/
  README.md SCOPE.md DISCLOSURE.md config.yaml requirements.txt Makefile CLAUDE.md
  src/tracefx/
    schema.py features.py baseline.py graph.py motifs.py ledger.py gate.py
    rollup.py explain.py actions.py replay.py casefile.py simulate.py evaluate.py
    pipeline.py cli.py types.py
  app/app.py  app/theme.css
  data/ seedA.csv seedB.csv seedC.csv truth_*.json demo_small.csv
  tests/ test_schema.py test_motifs.py test_hard_negatives.py test_gate.py test_pipeline.py
  reports/  (generated)
```
Makefile targets: `make setup`, `make data`, `make test`, `make demo`, `make eval`.

---

## 7. ROADMAP

**Tonight (prep, declare in README):** venv + deps + hello-world Streamlit; `types.py`, `config.yaml`, `simulate.py` (3 seeds, hard negatives, ring warm-up, non-round amounts); `evaluate.py`; frozen `Result` contract; repo + CLAUDE.md.

**Tomorrow:**
| Time | Task | Done when | Fallback |
|---|---|---|---|
| 10:00–10:30 | schema, features, baseline | scored table on seed A | rules-only |
| 10:30–11:30 | graph + M1, M2, M3 | ring = one component; hard negatives separate | keep M1+M2 |
| 11:30–12:15 | M4 cohort (with convergence rule) | cohort found; flash-sale not alerted | drop M4, note in scope |
| 12:15–12:45 | ledger, gate, why-not, actions | 4 demo cases correct; seed B holds | simple threshold |
| **12:45** | **KILL CHECK: Level 1 on A and B?** | yes → continue; no → freeze scope | — |
| 12:45–13:45 | UI: queue, ledger, why-not, ring graph, case file | clickable chain | table + PNG |
| 13:45–14:20 | replay (precomputed) + judge's pen | slider + lead time | skip pen |
| 14:20–14:40 | red-team, latency HUD, metrics panel | runs | skip |
| 14:40–15:00 | README, scope note, 90s recording, push | clean clone runs `make demo` | recording first |

**Levels:** 0 baseline table · 1 ledger + gate + motifs · 2 replay, pen, case file, red-team · 3 streaming engine, FastAPI, LightGBM, IEEE-CIS.
Cut order under pressure: A12 → A11 → A9 → A6 → A5 → A4 → A1. Never cut A2, ledger, gate, README.

---

## 8. DEMO DATA (deterministic)

- **Case A:** 10-account ring, shared sequence, warm-up behaviour, converges on one payee → FRAUD.
- **Case B:** legit high-value jewellery/phone purchase by an old account → LEGIT with why-not panel (baseline flags it).
- **Case C:** family-shared device + one large transfer → REVIEW with stated reason.
- **Case D:** traveller on a new device/city, otherwise normal → REVIEW or LEGIT, never FRAUD.
- **Hard negatives in the background:** hostel Wi-Fi, flash-sale cohort, landlord receiving rent.

**2-minute script:** calm ticker → replay → ring alert with lead time → evidence ledger → why-not on case B → judge's pen → red-team → close: "We show why we accuse, and why we don't."

---

## 9. METRICS (real runs only)

FP count on legit high-value · gate precision · ring recall (full / partial / missed) · account PR-AUC and precision@k · baseline vs TRACE-FX on seeds A/B/C · lead time and ₹ intercepted (simulated, labelled) · p50/p95 latency per tx.

---

## 10. TESTS

Normal · missing columns · duplicate tx_id · malformed timestamps · unknown payee/device · new account (cold start) · high-value legit · obvious fraud · small ring (3) · large ring (10) · burst · each hard negative (family device, hostel IP, flash sale, landlord, traveller) · forced motif exception → `degraded` set, no crash · forced graph exception → baseline table · forced viz exception → static table.

---

## 11. FAILURE BUDGET

| Component | Risk | Impact | Fallback |
|---|---|---|---|
| M4 sequence cohort | Med | lose the key differentiator | ship M1–M3, state in scope note |
| Ledger weights | Med | wrong labels | tune on A, verify B/C; manual threshold |
| PyVis rendering | Low | no diagram | static matplotlib/NetworkX PNG |
| Replay | Med | lose wow moment | use saved frames; else screen recording |
| Judge supplies odd CSV | Med | crash | mapping + degrade to behaviour-only |
| Install on judging machine | Low | no demo | recording + saved results |

Top catastrophic modes: (1) hard negatives merge into rings; (2) pipeline crash on unfamiliar CSV; (3) leaked synthetic data inflating metrics; (4) UI broken at demo; (5) missing README/scope note.

---

## 12. DISCLOSURE TABLE

| Resource | Type | Use | Ours |
|---|---|---|---|
| scikit-learn IsolationForest | library | behaviour score | features, gate |
| NetworkX, PyVis | libraries | graph, view | motifs, ledger |
| Streamlit, Jinja2 | libraries | UI, case file | app, templates |
| Synthetic generator | own code | all demo/eval data | all |
| AI coding assistants | tool | code drafting | review, tests, decisions |
| IEEE-CIS (only if used) | dataset | sanity run | adapter |

---

## 13. VIBE-CODING PACK

### 13.1 CLAUDE.md / .cursorrules (put in repo root)
```
Project: TRACE-FX fraud intelligence. Read PS04_MASTER_BLUEPRINT.md first.
Rules:
- Python 3.10, typed, dataclasses. Add NO new dependencies without asking.
- Pure functions; no globals; config from config.yaml.
- Every stage returns data; never touches UI. UI reads only pipeline.Result.
- Deterministic: seed everything.
- No GNN, no LLM calls, no Docker, no graph DB.
- Write the test first or together with the function. Run pytest before saying done.
- Keep functions < 40 lines. If a file grows > 250 lines, ask before splitting.
- On failure: show the full error, propose the smallest fix, do not rewrite files.
```

### 13.2 Workflow discipline
- One module per prompt. After each: `pytest` → green → `git commit`.
- Paste real error text, never "it doesn't work".
- Ask the AI to explain each motif in your own words before you accept it — judges will ask you.
- Freeze `types.py` early; changing it later breaks everything.
- Never let the AI refactor working code at hour 4.

### 13.3 Prompt sequence (copy in order)
1. "Create `types.py` with the dataclasses Evidence, LedgerLine, Decision, Group, Result exactly as in the blueprint §3.2, frozen where specified."
2. "Create `simulate.py`: `generate(seed, n_accounts, n_tx)` → (DataFrame, truth dict). Include: a 10-account ring with warm-up behaviour, shared sequence, convergence to one payee; and hard negatives: family device, hostel IP (30 accounts), flash-sale cohort (200 aged accounts, no sink), landlord receiving monthly rent, high-value legit purchases, a traveller. Non-round amounts, non-contiguous IDs. Write tests asserting truth counts."
3. "Create `schema.py`: `load(path, mapping=None)` and `quality_report(df)`; required/optional columns; dedupe; timestamp parsing; clear errors."
4. "Create `features.py` and `baseline.py` per blueprint §3.3; cold-start handling; return a 0–1 behaviour score."
5. "Create `graph.py` with typed edges and degree caps from config."
6. "Create `motifs.py`: M1, M2, M3 returning Evidence lists; unit tests on hand-built micro-datasets for each."
7. "Add M4 with n-gram inverted index and IDF weights; enforce the convergence rule; test that the flash-sale cohort yields no alert."
8. "Create `ledger.py`, `gate.py`, `rollup.py`, `explain.py`, `actions.py` per §3.3; templates must cite transaction IDs and timestamps; test the four demo cases and each hard negative."
9. "Create `pipeline.run` with per-stage try/except and `degraded` list; add fault-injection tests."
10. "Create `evaluate.py` and `cli.py`; print the metrics table for seeds A/B/C vs the IsolationForest baseline."
11. "Create `app/app.py` (Streamlit): ranked queue, ledger panel, why-not panel, ring subgraph (ring + 1 hop), action box; restrained theme, one accent colour; read only `Result`."
12. "Create `replay.py` (precompute ~40 checkpoint frames, lead-time calculation) and a timeline slider."
13. "Add judge's pen (edit a transaction, rerun on demo_small), then red-team (evasion level 0/1/2 in simulator)."
14. "Create `casefile.py` (Jinja2 HTML report) and the README, SCOPE.md, DISCLOSURE.md."

### 13.4 Debug protocol
Reproduce with a 20-row fixture → failing test → minimal fix → rerun full tests → commit. If a motif is stuck >30 minutes, cut it per the cut line and move on.

---

## 14. TOP JUDGE QUESTIONS (short honest answers)

1. **Why not a GNN?** Needs labels and training, hard to explain; the rubric rewards precision and explanation.
2. **How do you control false positives?** FRAUD needs two independent structural evidence types; exculpatory evidence subtracts; threshold chosen on a time-based validation window.
3. **Is the data synthetic?** Yes; evaluated on two unseen seeds with hard negatives; IEEE-CIS adapter is optional.
4. **Are the weights learned?** No — a transparent hand-set policy, tuned on seed A. We report sensitivity.
5. **What if fraudsters change devices?** Structural signals that don't depend on devices (sink convergence, sequence cohort) persist; shown in red-team.
6. **Is it real-time?** Batch with replay; per-transaction latency reported. True streaming is a stretch goal.
7. **What if the schema differs?** Column mapping + degrade to behaviour-only.
8. **What did you borrow?** See disclosure table.
9. **What is yours?** The ledger and gate policy, exculpatory evidence, sequence cohort with convergence rule, replay lead-time, red-team harness.
10. **What would break it?** Slow-drip fraud with no shared entities; it falls to REVIEW via behaviour only.

---

## 15. DEFINITION OF DONE

`make demo` works from a clean clone · four demo cases behave as specified · metrics printed for seeds A/B/C · tests green · README, scope note, disclosure complete · 90-second recording saved · repo public and submitted.

## 16. UNVERIFIED (check, don't assume)

Whether judges bring their own data · the real participant count · jury timings · any lead-time/₹ numbers (simulated only) · pre-built code acceptability (declare it).
