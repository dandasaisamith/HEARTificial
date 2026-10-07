# TRACE-FX
**Real-Time Financial Fraud Intelligence Engine**

TRACE-FX is an offline, CPU-only, locally-executable fraud detection system designed for the HNX26PSI04 Hackathon.

> **Don't just detect the fraud. Show the evidence, and show why we didn't accuse the innocent.**

## Key Features
- **Deterministic Engine**: The same data and config always yield the exact same decisions.
- **Evidence Ledger**: Every decision (FRAUD / REVIEW / LEGIT) is backed by an explicit point-based ledger. No black-box scores.
- **Structural Fraud Motifs**: Graph-based structural anomaly detection out-of-the-box (Shared Device, Common Sink, Pass-Through, Sequence Cohorts, Burst).
- **Causal Alerting**: Ensures no future information leaks into past alerts (`alert_ts`).
- **Fail-Soft Architecture**: Components gracefully degrade upon failure instead of crashing the pipeline.

## Quickstart

```bash
# Setup the environment
make setup

# Generate synthetic datasets for evaluation
make data

# Run the test suite
make test

# Evaluate the pipeline
make eval

# Launch the interactive Streamlit demo
make demo
```

## Structure
- `src/tracefx/` - Core detection engine, totally pure, headless.
- `app/` - Streamlit interactive demo dashboard.
- `tests/` - Comprehensive test suite.
- `docs/` - Architecture specs and rationales.
- `data/` - Synthetic data (generated via `make data`).
- `reports/` - Generated evaluation reports and replays.
