# DEMO — deterministic, 2 minutes

Dataset: `data/demo_small.csv` (seed 42, ~5k tx). Replay is `reports/replay.html` generated from `Result` (causal alert times). Nothing random at demo time.

## Cases
- **A ring:** 10 accounts, shared item sequence, converge on one payee -> FRAUD, ledger lists exact tx ids.
- **B legit high-value:** old account, known device, repeat payee -> LEGIT, why-not panel; baseline flags it.
- **C ambiguous:** family device + one large transfer -> REVIEW with stated reason.
- **D unusual-but-legit:** traveller, new device/city -> REVIEW or LEGIT, never FRAUD.

## Script
0-10s calm ticker, alerts=0 · 10-30s replay, ring assembles, alert with lead time (simulated) · 30-60s open ledger, show source rows · 60-80s case B shield, case C review · 80-105s judge's pen · 105-120s red-team, close: "We show why we accuse, and why we don't."

## Preflight checklist
[ ] clean clone runs `make demo` · [ ] reports/replay.html opens offline · [ ] screen recording saved · [ ] metrics printed from last `make eval` · [ ] browser zoom/theme checked · [ ] laptop on charger, notifications off · [ ] backup: recording + result.json
