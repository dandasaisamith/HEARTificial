# FOUNDATION AUDIT

## 1. Files That Exist
- **Root**: `AGENTS.md`, `DISCLOSURE.md`, `Makefile`, `README.md`, `SCOPE.md`, `config.yaml`, `requirements.txt`
- **Docs**: `ARCHITECTURE_LOCK.md`, `DATA_SPEC.md`, `CONTRACTS.md`, `ARCHITECTURE.md`, `GUARDRAILS.md`, `TASKS.md`, `DEMO.md`
- **Source (`src/tracefx/`)**: `__init__.py`, `__main__.py`, `actions.py`, `baseline.py`, `casefile.py`, `cli.py`, `config.py`, `evaluate.py`, `explain.py`, `features.py`, `gate.py`, `graph.py`, `ledger.py`, `motifs.py`, `pipeline.py`, `replay_html.py`, `rollup.py`, `schema.py`, `simulate.py`, `types.py`
- **App**: `app/app.py`
- **Tests**: `test_config.py`, `test_contracts.py`, `test_gate.py`, `test_motifs.py`, `test_pipeline.py`, `test_schema.py`

## 2. Files Expected by Architecture But Missing
- `GEMINI.md` (root, prompt itself but missing as a standalone file)
- `docs/SYSTEM_DESIGN.md` (to be created)
- `docs/DECISIONS_LOG.md` (created during this audit)
- `tests/fixtures/mock_result.json`
- `tests/fixtures/mock_evidence.json`
- `app/assets/`
- `requirements.lock.txt`
- `tests/test_mock_pipeline.py` (we have `test_pipeline.py` instead)

## 3. Files That Exist But Are Undocumented
- None of immediate consequence. The existing python files match the architecture explicitly.
- `CLAUDE.md`, `WALKTHROUGH.md`, `sai.md` in root (likely superseded/alternative environment docs).

## 4. Empty/Stub Files
- No empty Python stubs. Most files contain >2KB of functional logic/structure, with `simulate.py` being highly implemented.

## 5. Implemented Files
- Almost all files in `src/tracefx/` have substantial implementations, indicating that a significant amount of scaffolding and functional code has already been generated. `pytest` confirms that at least config, contracts, gate, motifs, pipeline, and schema tests are currently passing.

## 6. Duplicate/Conflicting Files
- `test_pipeline.py` exists instead of `test_mock_pipeline.py`. Kept `test_pipeline.py`.

## 7. Conflicting Names
- `TASKS.md` vs Architecture for `replay.py` -> `replay_html.py`. Addressed in `DECISIONS_LOG.md`.

## 8. Conflicting Function Signatures
- None discovered in standard interface scans.

## 9. Missing Tests
- There is no specific test for `baseline.py`, `ledger.py`, `features.py`, or `evaluate.py`. However, some may be covered functionally under `test_pipeline.py`.

## 10. Missing Fixtures
- `tests/fixtures/mock_result.json` and `tests/fixtures/mock_evidence.json` are absent and must be generated.

## 11. Dependency Problems
- `requirements.lock.txt` is missing.

## 12. Configuration Problems
- None apparent; `test_config.py` passes, meaning `config.yaml` is structurally valid against `config.py`.

## 13. Data Problems
- The `data/` and `reports/` directories exist but are empty. No seeds or demo datasets have been generated yet.

## 14. Unresolved Architectural Decisions
- The UI consumption of `mock_result.json` needs to be solidified by generating the mock fixtures and ensuring `app.py` has no imported dependencies on the tracefx internals.
