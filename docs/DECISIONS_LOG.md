# DECISIONS LOG

This log records structural, architectural, and implementation decisions made during the foundation phase where requirements were unspecified or documents conflicted.

## 1. Canonical Replay File Name
- **Conflict**: `TASKS.md` refers to `replay.py` while the locked architecture requires `replay_html.py`.
- **Decision**: Used `replay_html.py` as the single canonical name consistently, aligning with the higher-precedence architecture document.

## 2. Test Pipeline Naming
- **Conflict**: Prompt expects `test_mock_pipeline.py` but the repository contains an existing comprehensive `test_pipeline.py`.
- **Decision**: Retained `test_pipeline.py` as the canonical pipeline test suite rather than introducing an overlapping or duplicate test file.

## 3. GEMINI.md File
- **Observation**: `GEMINI.md` is specified as an architecture-defining file but it did not exist physically in the repository at the start of the session.
- **Decision**: The system provided this context inherently via the environment, so it will be formalized as part of the environment rules and no new empty placeholder is created, preserving the single source of truth.

## 4. Tests Directory Structure
- **Observation**: `tests/fixtures/mock_result.json` and `mock_evidence.json` are absent, as is `app/assets/`.
- **Decision**: Creating these missing directories and mock data generation logic so that the UI can consume the mock `Result` seamlessly, enabling parallel UI and ML development.
