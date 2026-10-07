---
description: Fallow this
---

# TRACE-FX — MASTER IMPLEMENTATION CONTROL PROMPT

You are implementing TRACE-FX, a fraud-intelligence system for HNX26PSI04.

THIS IS AN IMPLEMENTATION TASK, NOT AN ARCHITECTURE-DESIGN TASK.

The architecture has already been decided.

Your primary responsibility is:
1. read the authoritative documents,
2. obey the frozen contracts,
3. implement only the assigned task,
4. write tests,
5. run the tests,
6. verify the actual result,
7. report exactly what works.

Do NOT redesign the system.

============================================================
1. AUTHORITATIVE DOCUMENT ORDER
============================================================

When documents disagree, use this exact precedence:

1. docs/ARCHITECTURE_LOCK.md
2. docs/DATA_SPEC.md
3. docs/CONTRACTS.md
4. docs/TASKS.md
5. docs/ARCHITECTURE.md
6. docs/GUARDRAILS.md
7. AGENTS.md
8. GEMINI.md
9. SCOPE.md
10. DISCLOSURE.md
11. docs/DEMO.md

docs/BLUEPRINT.md and PS04_MASTER_BLUEPRINT.md are historical/reference documents only.

DO NOT use them to override the authoritative documents above.

If you find a contradiction:
- do not silently choose;
- apply the precedence order;
- record the decision in docs/DECISIONS_LOG.md;
- do not modify locked architecture unless the task explicitly authorizes it.

2. PROJECT PURPOSE
============================================================

TRACE-FX takes transaction data and produces:

- per-transaction risk
- per-account risk
- suspicious groups/rings
- discovered fraud pattern
- connection graph
- recommended action
- explicit explanation for every decision

Core pipeline:

CSV
→ schema + capability detection
→ temporal behavioural features
→ behavioural scorer
→ typed entity graph
→ fraud motifs M1-M5
→ evidence ledger
→ precision gate
→ FRAUD / REVIEW / LEGIT
→ account/group rollup
→ explanation/action
→ Result

The explanation is generated from the actual computation.

Do not generate explanations using an LLM.

============================================================
3. NON-NEGOTIABLE ARCHITECTURE
============================================================

Do NOT add:

- GNN
- GAT
- GraphSAGE
- TGN
- SHAP
- conformal prediction
- LLM calls
- Neo4j
- graph database
- Kafka
- FastAPI
- Docker
- microservices
- runtime cloud APIs
- database dependencies
- PyVis
- CDN dependencies

Runtime stack:

- Python >= 3.10
- pandas
- numpy
- scikit-learn
- networkx
- streamlit
- jinja2
- pyyaml
- pytest

LightGBM is optional and must only be used in the explicitly supported supervised branch.

CPU only.

Everything must work offline.

============================================================
4. CORE DESIGN RULE
============================================================

TRACE-FX is NOT:

raw data
→ black-box classifier
→ probability
→ explanation

TRACE-FX is:

raw data
→ behavioural signal
→ named structural detectors
→ evidence
→ exculpatory evidence
→ deterministic evidence sum
→ precision gate
→ decision

The ledger is part of the decision computation.

============================================================
5. CANONICAL INPUT CONTRACT
============================================================

Required columns:

tx_id
ts
payer_id
payee_id
amount

Optional:

tx_type
device_id
ip
merchant_id
item_id
channel
city
account_open_date
label

Never assume optional columns exist.

schema.py must expose capabilities describing which optional information is available.

If a capability is unavailable:
- disable only the dependent detector;
- do not crash;
- do not fabricate missing information;
- expose the disabled capability in Result.capabilities.

============================================================
6. CORE TYPES ARE FROZEN
============================================================

Do not change types.py unless explicitly instructed.

Evidence:

- type
- accounts
- tx_ids
- first_ts
- last_ts
- satisfied_at
- strength
- detail

LedgerLine:

- source
- points
- text
- tx_ids

Decision:

- tx_id
- label
- net_points
- risk
- ledger
- action
- alert_ts

Group:

- group_id
- accounts
- evidence_types
- risk
- shape
- summary

Result:

- tx
- accounts
- groups
- evidence
- decisions
- graph
- metrics
- degraded
- quality
- capabilities

============================================================
7. CAUSALITY IS NON-NEGOTIABLE
============================================================

No stage may use future information.

For any timestamp t:

the system may only use transactions with ts <= t.

Evidence.satisfied_at means:

"the earliest timestamp at which this evidence condition became true."

Decision.alert_ts means:

"the earliest timestamp at which the precision gate could legitimately fire."

Do not use dataset-end information to calculate an earlier alert.

Do not perform future-aware rolling features.

Do not leak truth labels into detector logic.

============================================================
8. BEHAVIOURAL SCORER
============================================================

features.py computes temporal behavioural features including:

- past-only amount behaviour
- account velocity
- new-payee behaviour
- new-device behaviour
- peer deviation
- time-of-day deviation
- novelty/drift where supported

All rolling features must be shifted so the current transaction cannot influence its own historical baseline.

baseline.py:

default scorer = IsolationForest.

Output must be numeric in [0,1].

Cold-start accounts must not receive artificial high risk simply because history is absent.

Behaviour score alone can NEVER produce FRAUD.

If supervised mode is explicitly enabled and labels are available, LightGBM may be used through the frozen scorer interface.

============================================================
9. GRAPH
============================================================

graph.py creates typed relationships.

Use hub caps.

Default:
device degree cap = 8
IP degree cap = 8

High-degree shared infrastructure must not automatically create fraud rings.

Graph construction does not make decisions.

Graph construction does not assign fraud labels.

============================================================
10. MOTIFS
============================================================

motifs.py produces Evidence objects.

It does NOT produce FRAUD/REVIEW/LEGIT labels.

M1:
shared device/IP between >=2 accounts where appropriate, subject to hub caps and prior-link constraints.

M2:
common sink:
>=4 distinct payers to a payee inside configured time window,
with cadence/history protection.

M3:
pass-through:
account receives money and sends >=80% onward within configured 30-minute window.

M4:
sequence cohort:
ordered item/merchant tokens
→ 3-grams
→ rare-IDF weighting
→ inverted index
→ cohort >=4
→ MUST converge on sink or pass-through.

M5:
burst:
1-hour activity significantly above own baseline,
with temporal clustering.

Every Evidence must include:

- exact accounts
- exact transaction IDs
- first timestamp
- last timestamp
- satisfied_at
- strength
- detector details

============================================================
11. LEDGER
============================================================

ledger.py converts actual signals into LedgerLine objects.

Positive examples:

behaviour anomaly
shared device
common sink
pass-through
sequence cohort
burst

Negative/exculpatory examples:

long tenure
known/repeated device
repeat payee
amount within normal range
amount within peer range

Every LedgerLine must be traceable to source transactions where applicable.

Do not write explanations that cannot be reproduced from the ledger.

Weights come from config.yaml.

Do not hard-code weights in detector logic.

============================================================
12. PRECISION GATE
============================================================

Default configuration:

fraud_net = 60
review_net = 30
fraud_min_structural_types = 2

FRAUD requires BOTH:

net_points >= fraud_net

AND

at least two independent structural evidence types.

Behaviour does not count as a structural evidence type.

Behaviour alone cannot produce FRAUD.

One structural motif alone cannot produce FRAUD.

Possible output labels:

FRAUD
REVIEW
LEGIT

REVIEW is a valid intentional result.

Exculpatory evidence can reduce a borderline FRAUD to REVIEW.

============================================================
13. ROLLUP
============================================================

Account risk uses the frozen noisy-OR strategy.

Groups are formed from evidence links.

Do NOT form fraud groups merely because accounts share a raw entity.

A shared high-degree Wi-Fi node alone is not a fraud ring.

============================================================
14. FAIL-SOFT REQUIREMENT
============================================================

A failure in one stage must not unnecessarily destroy the complete application.

Examples:

graph failure:
→ continue with behavioural/table result
→ add "graph" to degraded

motif failure:
→ behaviour-only result
→ no FRAUD from behaviour alone

visualisation failure:
→ show static result/table

Every degradation must be observable through Result.degraded.

Do not silently swallow exceptions.

============================================================
15. TEST-FIRST REQUIREMENT
============================================================

For every implementation:

1. inspect current code;
2. identify exact contract;
3. write or update tests;
4. implement smallest correct change;
5. run targeted tests;
6. run complete pytest;
7. only then report completion.

Do not claim success because code "looks correct".

Completion requires actual command output.

============================================================
16. FILE OWNERSHIP
============================================================

Only edit files explicitly assigned to you.

If assigned CORE:

schema.py
features.py
baseline.py
graph.py
their tests

If assigned DETECTORS:

motifs.py
motif tests

If assigned DECISION:

ledger.py
gate.py
rollup.py
explain.py
actions.py
their tests

If assigned UI:

app/app.py
replay_html.py
casefile.py
UI tests

If assigned PIPELINE:

pipeline.py
integration tests

Do not modify another lane's files to make your code work.

If an interface is insufficient:
STOP implementation of the cross-boundary change,
report the exact contract problem,
and propose the smallest contract-compatible solution.

============================================================
17. NO REFACTORING DURING IMPLEMENTATION
============================================================

Do not:

- rename unrelated functions
- reorganize the repository
- change public APIs
- rewrite working modules
- introduce abstractions without necessity
- replace existing libraries
- add dependencies
- "clean up" unrelated code

Prefer the smallest implementation satisfying the frozen contract.

============================================================
18. DATA LEAKAGE PROHIBITIONS
============================================================

Detector code MUST NOT:

- read truth JSON
- read synthetic ring metadata
- read hidden labels unless explicitly in supervised training mode
- detect fraud using simulator-specific IDs
- detect fraud using contiguous transaction IDs
- rely on planted ring account names
- rely on generated ordering artifacts

Truth files are evaluation-only.

============================================================
19. ACCEPTANCE TEST STANDARD
============================================================

A task is complete only when all of the following are true:

[ ] implementation exists
[ ] public signature matches CONTRACTS
[ ] unit tests pass
[ ] targeted edge cases pass
[ ] no future leakage
[ ] deterministic under fixed seed
[ ] no new dependency
[ ] no contract change
[ ] pytest passes
[ ] actual command output verified
[ ] no unrelated files changed

===========================