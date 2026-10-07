# ARCHITECTURE LOCK (v2) — honest audit, 14 answers, locked design, full dev cycle

I read the section-14 judge questions as "the 14 questions" (the blueprint lists 10 there; I added 4 harder ones). If you meant the 14 vibe-coding prompts, they are in docs/BLUEPRINT.md section 13.3 and are re-sequenced in Part G below.

---
## PART A — THE 14 JUDGE QUESTIONS, ANSWERED HONESTLY

**1. Why not a GNN?**
A GNN learns "ring-ness" from labelled examples. We have no labelled real rings, 5 hours, and a rubric that scores explanation. A GNN cannot say "accounts A and B share device D and both paid wallet W within 9 minutes". Honest cost: a GNN could discover ring shapes we did not hand-code. We cover that gap with the behaviour score plus the REVIEW tier, and the scorer is pluggable, so a GNN score could be added later without changing the pipeline.

**2. How do you control false positives?**
Five layers: (1) FRAUD needs two independent structural evidence types, never behaviour alone; (2) exculpatory lines subtract points (tenure, repeat payee, known device, normal amount); (3) hub caps stop shared Wi-Fi/big merchants from creating fake rings; (4) the sequence-cohort rule only counts if money also converges; (5) thresholds are chosen on a time-based validation window. Honest caveat: the official "FP cap" level is not stated in the booklet (UNVERIFIED), so we report precision twice — FRAUD-only and FRAUD+REVIEW — and show false positives on the legitimate high-value set at both tiers.

**3. Is the data synthetic? Isn't that circular?**
Yes, and it is the biggest weakness. If we plant a ring with exactly the traits our motifs look for, near-perfect results prove nothing. Mitigations: hard negatives that look like rings; ring variants (not all members share the device, noisy sequences, warm-up behaviour); seed C contains a ring type no motif targets, so we can show honest fallback to REVIEW or a miss; and an independent-generator sanity run if time allows (IBM AML-style data; availability UNVERIFIED). Say clearly: "these numbers are optimistic compared with real data."

**4. Are the evidence weights learned?**
No. They are a stated, hand-set policy tuned on seed A and reported on B/C. We publish the combination table (which evidence combinations reach FRAUD) and a weight-sensitivity check. If a labelled dataset is supplied, the same ledger lines become inputs to a tiny logistic regression, so weights can be fitted. That path is optional.

**5. What if fraudsters change devices or timing?**
Device sharing dies; sink convergence and the sequence cohort do not depend on devices. The red-team mode shows this live. If they also diversify sinks and randomise sequences, evidence falls and the ring degrades to REVIEW. We show that too. No system survives a perfect adversary.

**6. Is it real-time?**
Not as streaming ingestion. It is batch scoring with **causal alert times**: every evidence item records `satisfied_at`, the moment its condition first became true using only data up to that moment, so the alert time and lead time are what a live system would have produced. A prefix-equivalence test (run on the data up to time t, labels already fired must match) verifies no future leakage. We also report per-transaction latency. Say "causal replay", not "streaming".

**7. What if the schema changes?**
`schema.py` maps columns and runs a **capability report**: which optional columns exist, therefore which motifs are active. Missing device/IP disables M1; missing item/merchant disables M4. The UI states what is off. With only the required five columns the system degrades to behaviour + M2/M3 and says so.

**8. What did you borrow?**
IsolationForest and NetworkX (libraries), the idea of motif-based fraud-ring detection (standard in AML/fraud analytics), time-based evaluation practice, optionally LightGBM. See DISCLOSURE.md.

**9. What is actually yours?**
Nothing algorithmically new. What is ours: the composition and discipline — exculpatory evidence as a first-class output, the convergence rule, causal alert time with lead time, a hard-negative test bed, and an adversary harness. Do not say "novel".

**10. What would break it?**
Slow-drip fraud with no shared entities; fraudsters who diversify sinks; a legitimate new customer making a huge purchase with no history (lands in REVIEW, by design); coincidental legitimate structure we did not model; data with no entity columns.

**11. Isn't this just a bank rules engine with weights?**
Largely yes, and that is how real fraud operations work: rules/evidence plus an ML score. We chose the hybrid deliberately because it is auditable. Our additions over a plain rules engine are the unsupervised behaviour score, the exculpatory side, the group/ring rollup, and the testing discipline. Own it; do not disguise it as AI magic.

**12. Why should we trust your recall?**
Report recall on ring members and on transactions, per seed, with baseline on the same alert volume. Seed C includes a ring type we do not detect; we show it. If recall on unseen seeds is lower than on A, say so.

**13. What if the judges give a dataset with no accounts (e.g. anonymised card data)?**
Then there is no graph to build; capability report shows motifs off, and only behaviour scoring runs. If labels are present, the supervised scorer (LightGBM, time split) takes over. The booklet explicitly allows simulated data ("create, find, or simulate your own"), so the demo does not depend on judges' data.

**14. Two rings share an account, or one account is in several groups?**
Groups are connected components over evidence links, so overlapping rings merge into one group; the ledger still lists each evidence item separately, so the explanation shows both structures. Honest limit: we do not separate overlapping rings into clean sub-rings.

---
## PART B — DEFAULT AI STRATEGY vs OURS

| Aspect | Default AI answer | Ours | Does a judge see the difference? |
|---|---|---|---|
| Framing | Classify transactions | Decide and justify an accusation | Yes (first screen) |
| Data | IEEE-CIS / Kaggle CSV | Own simulator with hard negatives + unseen seeds | Yes if they ask |
| Features | Amount, time, frequency | Per-account baseline + peer percentile + drift | Slightly |
| Model | GraphSAGE/XGBoost | IsolationForest (LightGBM if labels) | Not visible |
| Graph | Input to a GNN, shown as hairball | Evidence structure; ring + 1 hop only | Yes |
| Ring detection | Shared device or learned | 5 motifs incl. sequence cohort w/ convergence | Yes (rubric example) |
| Explanation | SHAP bars | Evidence ledger + exculpatory lines + source rows | Yes (biggest) |
| Threshold | 0.5 | Gate + two-structural-types rule | Indirectly |
| Uncertainty | none / fake conformal | REVIEW tier | Yes |
| Evaluation | accuracy/F1/ROC | FP on legit high-value, ring recall, precision@k, lead time | Yes |
| Time | random split | time split + causal evidence | Only if asked |
| Demo | static dashboard | scrubbable causal replay | Yes |
| Process | one big notebook | contract-first, tests, fail-soft | Repo reviewers |

## PART B2 — WHAT IN OUR PLAN IS REAL vs TABLE STAKES vs DECORATION

| Component | Class | Decision |
|---|---|---|
| Evidence ledger with exculpatory lines | REAL differentiator | Keep, centre of the demo |
| Convergence rule for sequence cohorts | REAL | Keep |
| Hard-negative test bed + unseen seeds | REAL (invisible unless shown) | Keep, show a results table |
| Causal alert time + lead time | REAL | Keep (replaces precomputed prefix frames) |
| Red-team harness | REAL but optional | Keep if time |
| Behaviour score, hub caps, M1-M3, schema mapping, time split | TABLE STAKES | Build, don't pitch |
| Judge's pen, source-row re-verify, case file | Useful, cheap | Keep minimal |
| Ring "shape" label, action simulator, precision dial, FastAPI, sleeper flag | DECORATION | **Cut** (sleeper only if it falls out free) |
| "Crowd will build GNN+SHAP" | UNVERIFIED assumption | Don't state as fact |
| "Hard to copy" | Overstated | A strong team can copy the idea in 3-4h; our edge is tested hard negatives + polish |

---
## PART C — HONEST AUDIT: WHAT WAS WRONG IN v1 AND THE FIX

1. **Circular evaluation** (we write motifs and the planted ring). Fix: ring variants, hard negatives, seed C with an undetected ring type, tx/ring-level ground truth separate from input, `label` never read by motifs (test enforces).
2. **IsolationForest is weak if judges provide labels.** "Catch most fraud" then favours a supervised model. Fix: pluggable scorer; if `label` exists in a training window, fit LightGBM (time split); else IsolationForest.
3. **Entity-poor data silently disables the graph.** Fix: capability report + UI badge.
4. **Replay by 40 prefix reruns is clunky and slower.** Fix: every Evidence gets `satisfied_at`; alert time = time the gate conditions were first met; replay = filter by time. One test proves causality.
5. **Streamlit reruns make smooth animation hard.** Fix: generate one self-contained HTML (vis-network inlined, offline-safe) with a JS time slider; Streamlit embeds it; the same file is the offline backup demo.
6. **Weights untested as combinations.** Fix: lock a combination table (below) and test it.
7. **Tx-level label semantics undefined.** Fix: locked rule (Part E-L2).
8. **"FP cap" unknown.** Fix: report both tiers; target zero FRAUD on the legit high-value set.
9. **Over-scoped extras.** Fix: cuts in B2.

---
## PART D — HOW IT WORKS, IN NEURAL-NETWORK / ML-PIPELINE TERMS

Think of TRACE-FX as a small **hand-wired, glass-box network** instead of a trained one:

- **Input layer** = `schema.py`. Clean, typed transactions.
- **Feature layer** = `features.py` + scorer. Turns raw rows into "how unusual is this vs this account's normal and vs its peers" (0-1). This is the only part that *learns* (IsolationForest, or LightGBM if labels).
- **Hidden layer = detector neurons.** Each motif is a neuron that fires only on one pattern: shared device, common sink, pass-through, sequence cohort, burst. Each outputs a strength and the exact transactions that made it fire.
- **Weighted sum = the ledger.** Each neuron's output is multiplied by a weight (points). Exculpatory neurons have negative weights (tenure, repeat payee, known device). Unlike a normal network, you can read every term.
- **Activation = the gate.** Not a sigmoid; a rule: net points above a line AND at least two *different* structural neurons fired (a two-key rule). This is why a single noisy signal cannot trigger an accusation.
- **Output layer** = FRAUD / REVIEW / LEGIT, plus account risk (noisy-OR across transactions), plus group (connected evidence).
- **Training** = we tune weights on seed A (train), check on B/C (validation/test), like any ML split. **Loss** is asymmetric: a false accusation costs more than a miss, which is the gate. **Backprop** is replaced by reading the ledger and fixing the weight that caused a wrong answer.
- **Where it differs from the default:** the default pipeline is *features -> black box -> probability -> post-hoc explanation*. Ours is *features -> named detectors -> readable sum -> rule gate*; the explanation **is** the computation, not an afterthought.
- **Honest bridge:** if labels exist, replace hand weights with logistic regression over ledger lines, which is literally one learned layer on the same neurons.

---
## PART E — WHAT MUST BE DECIDED BEFORE LOCKING (and my decisions)

| # | Decision | Locked value |
|---|---|---|
| L1 | Contract deltas | `Evidence.satisfied_at`, `Decision.alert_ts`, `Result.capabilities`; scorer interface `Scorer.fit(df_train)->self; Scorer.score(df)->Series` |
| L2 | Tx labelling | Evidence points attach to the tx_ids in that Evidence. An account in a FRAUD group gets account label FRAUD. Its other tx are REVIEW unless they hold evidence themselves |
| L3 | Combination table | See below |
| L4 | Ground truth | Separate `truth_<seed>.json`: rings (members, sink, devices, start, cashout tx ids, type), hard negatives (kind, accounts, tx ids), `high_value_legit_tx_ids`, per-tx `is_fraud`. Input CSV has no label unless supervised mode is on |
| L5 | Metrics | FP on legit high-value (amount >= p99, truth legit) at FRAUD and FRAUD+REVIEW; gate precision; ring recall (full >=80% members in one group / partial / missed); precision@10/50 and PR-AUC at account level; lead tx = ring outflow tx after alert_ts; intercepted = sum of their amounts; baseline = IsolationForest at same alert volume |
| L6 | Causality | Evidence uses only rows with ts <= satisfied_at; prefix-equivalence test on 3 checkpoints |
| L7 | UI | Streamlit shell + one self-contained HTML replay (vis-network inline) |
| L8 | Data policy | Simulated primary; independent-generator sanity optional; capability report for unknown CSV |
| L9 | Scorer | IsolationForest default; LightGBM when `label` present and `--supervised` |
| L10 | Scale | demo ~5k tx (<2s), eval ~50k (<30s), UI refuses >200k with a message |
| L11 | Solo protocol | trunk-based, commit per green task, tag `v-working` after each level |
| L12 | Cuts | ring-shape label, action simulator, dial, FastAPI |

**Combination table (default weights; verify by test):**
| Evidence present | Net (excl. exculpatory) | Result |
|---|---|---|
| M2+M4 (+M1) | 30+25(+20)=55..75 | FRAUD only if net>=60: needs M1 or behaviour or M3 as well |
| M1+M2+M4 | 75 | FRAUD |
| M2+M3 | 55 (+behaviour up to 20) | FRAUD if behaviour>=5 pts, else REVIEW |
| M1+M2 | 50 | REVIEW unless behaviour >=10 |
| Any single structural type | <=30 | REVIEW at most |
| Behaviour only | <=20 | LEGIT/REVIEW |
Exculpatory can pull a borderline FRAUD down to REVIEW. If the planted ring (M1+M2+M4) loses points from exculpatory lines and falls under 60, adjust the exculpatory caps, not the gate.

---
## PART F — LOCKED SYSTEM DESIGN (v2)

```
CSV -> schema(+capabilities) -> features -> Scorer(IF | LightGBM)
                 \                                  |
                  +-> graph(hub caps) -> motifs(M1-M5, each Evidence has satisfied_at)
                                               \    |
                                             ledger(+/-) -> gate -> alert_ts (causal)
                                                              -> rollup (account, group)
                                                              -> explain/actions -> Result
Result -> app.py (Streamlit) | cli.py | replay_html.py | casefile.py | evaluate.py
```
Causal alert time: for each decision, `alert_ts = max(tx.ts, satisfied_at of the evidence types required to meet the gate)`; the gate is evaluated in time order so the first moment the conditions hold is the alert. Replay shows nodes/edges by timestamp and fires the alert marker at `alert_ts`.

Simulator spec (so the data is not trivial): 60 days; ~2,000 accounts (demo 600); each account has 5-15 repeat payees, 1-2 devices, a home IP, lognormal amounts, item preferences from a Zipf catalogue; ring = 10 accounts, 70-90% on a shared device, noisy common sequence, warm-up of 2-4 weeks of normal behaviour, converge on one sink then pass-through; plus the hard negatives of GUARDRAILS.md; seed C adds a cyclic-transfer ring that no motif targets.

---
## PART G — FULL DEV CYCLE, STEP BY STEP
> Step content is valid. The CLOCK SCHEDULE is superseded by docs/TASKS.md v3 (parallel lanes). Where they differ, TASKS.md wins.

Format: Goal / Do (agent prompt gist) / Output / Validate / If it fails. Tonight = G0-G5. Tomorrow 10:00-15:00 = G6-G15.

**G0 Lock (30m).** Do: apply Part E to CONTRACTS.md and config.yaml (done in this repo). Output: frozen contracts. Validate: you can state each L1-L12 in one sentence. Fail: decide by coin-flip rather than stall; revisit only if a task proves it wrong.

**G1 Scaffold (20m).** Do: `make setup`, folders, empty modules with docstrings, pytest runs. Output: green empty test run. Validate: `make test`. Fail: drop lightgbm from requirements.

**G2 Types + config loader (15m).** Do: types.py exactly as CONTRACTS; `config.load()`. Validate: import test + config keys test.

**G3 Simulator (75m).** Do: generate(seed,n_accounts,n_tx) -> (df, truth); implement normal behaviour, ring with variants, 7 hard negatives, seed C cyclic ring, red-team evasion levels. Validate: truth counts; no contiguous IDs; ring accounts' warm-up looks normal (assert behaviour stats not extreme); `label` absent from df. Fail: simplify population size, keep ring + 4 hard negatives.

**G4 Evaluator (35m).** Do: metrics of L5, baseline at same alert volume; prints a table; stub scorer ok. Validate: running on truth-as-prediction gives perfect scores; random prediction gives near zero. Fail: precision + FP only.

**G5 Schema + capabilities (30m).** Do: mapping, dedupe, UTC parse, quality report, capability dict. Validate: tests for missing optional columns, duplicates, malformed timestamps, missing required (clear error). Fail: skip mapping UI, keep canonical names.

**G6 Features + Scorer (35m).** Do: per-account rolling baselines using only past data (shift!), peer percentile, velocity, novelty; IsolationForest scorer; LightGBM branch behind flag. Validate: no feature uses future rows (test); score in [0,1]; cold start neutral. Fail: z-score rule scorer.

**G7 Graph (20m).** Do: typed edges, deg caps. Validate: hostel IP yields no links. Fail: skip IP edges.

**G8 Motifs (110m).** M1, M2, M3 first (60m) then M4 (50m); each returns Evidence with `satisfied_at`. Validate per motif on a 20-row fixture; hard-negative tests (family device, landlord, flash sale). Fail: ship M1-M3 and mark M4 NOT DONE in SCOPE.md.

**G9 Ledger, gate, rollup, explain, actions (45m).** Do: per Part E. Validate: combination-table test; demo cases A-D correct on seed A and B; every Decision has >=1 ledger line. Fail: single threshold + motif counts.

**G10 Pipeline + fail-soft + causality (30m).** Do: `_safe` wrapper; degraded list; prefix-equivalence test. Validate: fault-injection tests (motif/graph/viz exceptions) leave a usable Result. Fail: remove causality test only if time is gone, and drop the "causal" claim.

**KILL CHECK (12:45).** Level 1 correct on A and B with hard negatives present? If not, freeze scope, jump to G14.

**G11 CLI + eval run (20m).** `python -m tracefx score`, `make eval`. Validate: results table on A/B/C committed to `reports/`. Fill sai.md table from it only.

**G12 UI shell (60m).** Ranked queue, ledger panel, why-not panel, ring subgraph, capability badge, latency HUD, source rows. Validate: clean clone runs `make demo`; four cases clickable. Fail: table + static PNG.

**G13 Replay HTML + pen + case file (50m).** replay_html.py (inline JS, offline); pen reruns demo_small; casefile.py via Jinja2. Validate: open replay.html offline; edit a tx and see ledger update. Fail: static frames slider; skip pen.

**G14 Red-team + docs + recording (30m).** Evasion toggle, README, SCOPE.md, DISCLOSURE.md, 90s recording. Validate: someone else follows the README. Fail: recording first.

**G15 Submit (10m).** Public repo, form link, tag `v-final`. Validate: clone into a fresh folder, `make demo`.

Rule through all steps: commit when green; if a step runs 30 minutes over, apply its fallback and record it in SCOPE.md.

---
## PART H — FINAL HONESTY CHECK
- Our edge is explanation quality, restraint, and testing rigor, not a smarter model.
- Results are on our own generator; present them as such.
- Without entity columns the system is only a behaviour scorer; the UI says so.
- If the demo ring is found only because we planted its exact features, say that and point to ring variants, seed C and the hard negatives.
