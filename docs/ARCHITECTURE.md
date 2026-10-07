# ARCHITECTURE

```
CSV -> schema -> features -> baseline ----------------+
          \                                           v
           +-> graph -> motifs(M1..M5) -> ledger -> gate -> rollup -> explain/actions -> Result
                                                                         |
                                           app.py   cli.py   replay.py   casefile.py   evaluate.py
```

## Dependency rule (arrows point to what may be imported)
`types` <- `schema` <- `features` <- `baseline`; `types` <- `graph` <- `motifs`; `ledger` <- (baseline, motifs); `gate` <- `ledger`; `rollup` <- `gate`; `pipeline` <- all of the above; `app, cli, replay, casefile, evaluate` <- `pipeline` **only**. No cycles. `simulate` imports nothing from the engine.

## Modules
| Module | Responsibility | Never does |
|---|---|---|
| schema | map/validate/dedupe/parse, quality report | scoring |
| features | account baselines, peer percentiles, velocity, drift | graph work |
| baseline | IsolationForest -> 0..1 | decisions |
| graph | typed edges, hub caps | scoring |
| motifs | M1 shared device, M2 common sink, M3 pass-through, M4 sequence cohort, M5 burst, sleeper | labels |
| ledger | evidence (+) and exculpatory (-) lines with text and tx ids | thresholds |
| gate | FRAUD/REVIEW/LEGIT from net points + structural types | UI |
| rollup | account risk (noisy-OR), groups (components over evidence links), shape label | |
| explain/actions | deterministic templates, action policy | LLMs |
| pipeline | orchestration, fail-soft wrapper, degraded list | |

## Algorithms in one line each
- M1: device/IP linked to >=2 accounts with no prior payer/payee link; hub-capped.
- M2: payee with >=4 distinct payers in 24h; reduced if payee has cadenced repeat payers.
- M3: money in then >=80% out within 30 min; chains weigh more.
- M4: per-account ordered item tokens -> 3-grams -> IDF-weighted -> inverted index -> cohorts >=4 -> counts only if it converges on a sink/pass-through.
- M5: 1h burst vs own baseline (z>3) plus clustered start times.
- Account risk = 1 - prod(1 - p_i). Group = connected components over evidence links.

## Performance
Vectorised pandas groupby; inverted indexes (device->accounts, payee->payers, ngram->accounts) keep everything O(N). Target: demo_small (~5k tx) < 2s end to end; eval sets (~50k tx) < 30s. Replay is causal: Evidence.satisfied_at + Decision.alert_ts drive a self-contained HTML time slider (no prefix reruns).

## Failure behaviour
Each stage wrapped by `pipeline._safe(stage, fallback)`: on error log, add stage to `degraded`, use fallback (motifs fail -> behaviour-only labels capped at REVIEW; graph fails -> table without diagram; viz fails -> static table).

## Why these choices
Rubric rewards precision, evidence and rings; a deterministic ledger gives all three without training, and is explainable line by line. Hand-set weights are a stated policy, validated on unseen seeds, not a claim of learned optimality.
