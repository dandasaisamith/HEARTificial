# TASKS v3 — parallel lanes, clock-locked. Supersedes any older schedule.
Build window: tomorrow 10:00-15:00. Tonight = prep (data creation + scaffolding; declare in README). Agents work in parallel lanes on DISJOINT files, so there are no merge collisions. Everyone commits to trunk: `git pull --rebase` before push.

## Tonight (prep)
- [ ] P1 Prompt 1 run: scaffold, frozen types/config, stubs, mock fixture, contract tests, SYSTEM_DESIGN.md (owner: architect agent)
- [ ] P2 `simulate.py` + `make data` per docs/DATA_SPEC.md; generator tests green; demo_small committed
- [ ] P3 `evaluate.py` per ARCHITECTURE_LOCK L5; sanity: truth-as-prediction = perfect, random ~ 0
- [ ] P4 vendor vis-network into `app/assets/`; `pip freeze > requirements.lock.txt`; `make test` green

## Tomorrow
| Clock | Lane / task | Files (exclusive owner) | Done when |
|---|---|---|---|
| 10:00-10:15 | Sync: clone, `make setup`, `make data`, `make test` | - | green |
| 10:15-11:15 | **L1 Core** | schema.py features.py baseline.py graph.py | scored table on demo_small; capabilities dict; hostel IP yields no links |
| 10:15-11:15 | **L2 Detectors A** M1, M2, M3 (+ satisfied_at) | motifs.py | ring found as one component on demo_small; family/landlord not FRAUD-grade |
| 11:15-12:00 | **L2 Detectors B** M4 (n-gram inverted index + convergence rule), M5 | motifs.py | cohort found; flash-sale gives no alert |
| 10:15-11:30 | **L3 Decision** against fixture Evidence lists | ledger.py gate.py rollup.py explain.py actions.py | combination-table tests green; causal alert_ts |
| 10:15-12:15 | **L4 UI** against `tests/fixtures/mock_result.json` | app/app.py replay_html.py | queue, ledger, why-not, ring graph, time slider all work on the mock |
| 12:00-12:30 | **Integration** (architect/owner) | pipeline.py (turn mock off) | `make eval` runs on A, B |
| 12:30-12:45 | Eval + prefix-equivalence test | tests/ | numbers printed |
| **12:45** | **KILL CHECK**: Level 1 correct on A and B with hard negatives present? yes -> continue; no -> freeze scope, go to 14:00 block | | |
| 12:45-13:30 | Hook UI to real Result; case file; judge's pen | app/ casefile.py | four demo cases clickable |
| 13:00-13:15 | Lunch (fixed) | | |
| 13:30-14:00 | Red-team toggle, fault-injection tests, latency HUD, CLI | cli.py tests/ | failures degrade, no crash |
| 14:00-14:30 | README, SCOPE.md, DISCLOSURE.md, fill sai.md table from `make eval`, 90 s recording | docs | clean clone runs `make demo` |
| 14:30-15:00 | Buffer, tag `v-final`, public push, form submit | | submitted |

Cut order: red-team -> judge's pen -> case file -> M5. Never cut: ledger, gate, why-not, README, SCOPE.md.
If a task overruns 30 min: apply fallback (M4 -> mark NOT DONE; replay -> static frame slider; UI -> table + PNG), log in docs/DECISIONS_LOG.md.
