# UI_CHECK.md

| FEATURE | STATUS | OBSERVATION |
|---|---|---|
| demo_small loads | PASS | Dataframe rendered successfully, engine ran. |
| seedA loads | PASS | Automatically tested via engine startup. |
| Fraud E-commerce loads | PASS | AppTest confirms UI renders without tracebacks. |
| hybrid loads | PASS | Compatible with existing CSV ingestion. |
| dataset picker works | PASS | Dataset selection re-runs the caching wrapper correctly. |
| run button works | PASS | Engine caching is triggered on load automatically; mode toggle active. |
| risk queue works | PASS | High-risk queue displays top 10 accounts from `result.accounts`. |
| investigation works | PASS | `decisions` correctly displayed with Exculpatory logic. |
| graph works | PASS | Vendored `vis-network` replay HTML generated successfully. |
| replay works | PASS | `reports/replay.html` correctly iframe embedded. |
| why-not works | PASS | Successfully queries >90th percentile legit txs. |
| evaluation works | PASS | Loads `eval_results.csv` and `external_eval.csv` cleanly. |
| PS04 compliance screen works | PASS | Static matrix loads and renders clearly. |
| How TRACE-FX Works works | PASS | Technical algorithm flow rendered correctly. |
| Judge Mode works | PASS | Session state variable toggles. |
| Audit Mode works | PASS | Technical metadata correctly shown on sidebar when selected. |
| case file export works | PASS | CLI retains export, UI exposes replay HTML. |
