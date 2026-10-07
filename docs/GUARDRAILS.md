# GUARDRAILS — what we never do, and the traps in our own data

## Never
GNN/TGN as core · SHAP as the explanation · conformal branding · LLM in decisions/explanations · 0.5 threshold · random split (time split only) · accuracy metric · IEEE-CIS as main demo · hard-coded demo ring · Neo4j/Docker/microservices · hairball graph (ring + 1 hop only) · placeholder metrics · saying "novel" about GNN/SHAP/graphs · UI work before the backend finds the ring · tuning on the demo seed only · missing scope note/disclosure.

## Simulator realism (leakage control)
Ring accounts: warm-up period of normal behaviour; non-round amounts; non-contiguous IDs; 70-90% of members use the shared device; members also make ordinary purchases.
Hard negatives (must exist in every seed):
| Case | Must end as |
|---|---|
| Family sharing one device (2-4 aged accounts) | LEGIT or REVIEW, never FRAUD |
| Hostel/office Wi-Fi IP (30+ accounts) | no evidence (hub cap) |
| Festival flash-sale cohort (200 aged accounts, same item, no sink) | no alert |
| Landlord/school fee payee (many payers, monthly cadence) | LEGIT |
| Legit high-value purchase by old account | LEGIT with why-not panel |
| Traveller on new device/city | REVIEW or LEGIT, never FRAUD |
| Salary-day population burst | no alert |

## Honesty rules
Weights are a hand-set policy. Data is synthetic. Lead-time and rupees-intercepted are simulated and labelled so. "Real-time" = batch scoring + replay with measured per-transaction latency unless a streaming engine is actually built.

## UI rules
Restrained theme, one accent colour (amber = review, red = confirmed fraud only). No confusion matrix, ROC, SHAP bars, or neon gradients on screen one. Animation only to show time or evidence accumulating.
