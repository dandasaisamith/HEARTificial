# AGENTS.md — read this first, every session

**Project:** TRACE-FX — fraud intelligence for HNX26PSI04. Behaviour score + typed entity graph + 5 fraud motifs -> evidence ledger -> precision gate -> FRAUD / REVIEW / LEGIT, with an explanation for every score.
**Goal:** a working, explainable, demo-reliable system. Not the smartest model. The most defensible decision.

## Read order
1. This file  2. `docs/TASKS.md` (find the next unchecked task)  3. `docs/CONTRACTS.md` (types, config, signatures)  4. `docs/ARCHITECTURE.md` (only if you touch module boundaries)  5. `docs/GUARDRAILS.md` (before writing data or UI code)

## Commands
```
make setup   # venv + deps
make data    # generate seeds A,B,C + demo_small
make test    # pytest -q
make eval    # metrics table, baseline vs TRACE-FX, seeds A/B/C
make demo    # streamlit run app/app.py
python -m tracefx score data/seedA.csv --out reports/   # headless
```

## Hard rules
- Python 3.10, type hints, dataclasses. **No new dependency** without asking. Allowed: pandas numpy scikit-learn networkx pyvis streamlit jinja2 pyyaml pytest (optional: lightgbm, fastapi).
- **No** GNN/TGN, conformal prediction, LLM calls, Docker, graph DB, microservices, SHAP in the main path.
- Pure functions. No globals. All thresholds/weights live in `config.yaml`; never hard-code them.
- The UI, CLI and tests consume **only** `pipeline.run(df, cfg) -> Result`. Never import motifs/ledger from `app/`.
- Deterministic: every random call takes a seed.
- `src/tracefx/types.py` is frozen. Do not edit it without explicit approval.
- Every pipeline stage must fail soft: catch, log, append to `Result.degraded`, continue.
- Every score shown to a user must carry a ledger/explanation. No explanation = bug.
- Never print or display a metric that did not come from a real run.

## Working agreement
- One task at a time, from `docs/TASKS.md`. Small diffs. Do not refactor working code.
- Write/extend the test with the function. Run `make test` before saying done.
- When something fails: show the full error, reproduce with a <=20-row fixture, apply the smallest fix. Never rewrite a file to fix a bug.
- Commit after every green task: `git commit -m "T07: sequence cohort + tests"`.
- If a task is blocked >30 min, stop, apply its listed fallback, mark it in `docs/TASKS.md`, move on.
- Ask before: changing a contract, adding a dependency, deleting files, changing weights beyond what a task says.

## Definition of done (per task)
Code + tests green + acceptance command in `docs/TASKS.md` passes + task checkbox ticked + committed.

## Ownership map (avoid merge conflicts)
Builder: `src/`, `data/`, `tests/`. UI person: `app/`, `docs/DEMO.md`, README. Nobody else edits `src/` or `types.py`.

## Gotchas
- Shared Wi-Fi/IP and big merchants merge unrelated accounts: always apply degree caps (`graph.deg_cap`).
- Parse timestamps to UTC once, in `schema.py`.
- Sequence-cohort evidence counts **only** if the cohort also converges on a sink or pass-through. This is what stops flash-sale false positives.
- Behaviour score alone can never produce FRAUD.
- Group = connected components over *evidence links*, not raw shared entities.
