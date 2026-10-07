# CONTRACTS — types, config, signatures (frozen unless approved)

## Canonical input schema
Required: `tx_id, ts, payer_id, payee_id, amount`
Optional: `tx_type (MERCHANT|P2P), device_id, ip, merchant_id, item_id, channel, city, account_open_date, label`. Full generator spec: docs/DATA_SPEC.md
`schema.load(path, mapping=None) -> DataFrame` maps columns, dedupes on tx_id, parses ts to UTC. `schema.quality_report(df) -> dict`.

## types.py
```python
from dataclasses import dataclass, field
import pandas as pd

@dataclass(frozen=True)
class Evidence:
    type: str            # shared_device | common_sink | pass_through | sequence_cohort | burst
    accounts: tuple
    tx_ids: tuple
    first_ts: str
    last_ts: str
    satisfied_at: str     # ts when this evidence's condition first became true (causal)
    strength: float      # 0..1
    detail: dict = field(default_factory=dict)

@dataclass(frozen=True)
class LedgerLine:
    source: str          # e.g. "common_sink", "tenure_over_1y"
    points: float        # + evidence, - exculpatory
    text: str            # human sentence citing tx ids / timestamps
    tx_ids: tuple = ()

@dataclass
class Decision:
    tx_id: str
    label: str           # FRAUD | REVIEW | LEGIT
    net_points: float
    risk: float          # 0..1
    ledger: list
    action: str
    alert_ts: str        # causal time the gate conditions were first met

@dataclass
class Group:
    group_id: str
    accounts: tuple
    evidence_types: tuple
    risk: float
    shape: str           # star_mule | chain | cohort | mixed
    summary: str

@dataclass
class Result:
    tx: pd.DataFrame            # per-tx scores + labels
    accounts: pd.DataFrame      # per-account risk + label
    groups: list
    evidence: list
    decisions: dict             # tx_id -> Decision
    graph: dict                 # nodes/edges json for the ring view
    metrics: dict
    degraded: list              # names of stages that failed soft
    quality: dict
    capabilities: dict          # which motifs are active given the columns present
```

Scorer interface: `fit(df_train) -> self`, `score(df) -> pd.Series` (IsolationForest default; LightGBM if `label` present and supervised mode on).

## Signatures
```python
schema.load(path, mapping=None) -> pd.DataFrame
features.build(df, cfg) -> pd.DataFrame
baseline.score(feat, cfg) -> pd.Series            # 0..1 behaviour score
graph.build(df, cfg) -> nx.MultiGraph
motifs.find_all(df, G, cfg) -> list[Evidence]
ledger.build(df, behaviour, evidence, cfg) -> dict[str, list[LedgerLine]]
gate.decide(ledger, evidence, cfg) -> dict[str, Decision]
rollup.accounts(decisions, df) -> pd.DataFrame ; rollup.groups(evidence, decisions) -> list[Group]
explain.chain(group_or_decision) -> str
actions.recommend(decision_or_group) -> str
pipeline.run(df, cfg) -> Result
replay_html.render(result, path) -> None   # self-contained HTML, vis-network inlined
casefile.render(result, group_id) -> str (HTML)
evaluate.report(seed_paths, cfg) -> pd.DataFrame
```

## config.yaml (starting values; tune on seed A only, report on B/C)
```yaml
seed: 42
graph: {deg_cap_device: 8, deg_cap_ip: 8}
features: {window_short_h: 1, window_long_h: 24, tenure_days_protect: 365}
baseline: {contamination: 0.02, behaviour_flag_pct: 0.97}
motifs:
  common_sink: {min_payers: 4, window_h: 24}
  pass_through: {min_ratio: 0.8, window_min: 30}
  sequence: {ngram: 3, min_shared_rare: 2, min_cohort: 4, idf_rare_quantile: 0.9, require_convergence: true}
  burst: {z: 3.0, window_h: 1}
  sleeper: {dormant_days: 90}
points:
  behaviour_max: 20
  shared_device: 20
  common_sink: 30
  pass_through: 25
  sequence_cohort: 25
  burst: 10
  sleeper: 10
  tenure_over_1y: -15
  repeat_payee_3plus: -20
  known_device_5plus: -10
  amount_within_p95: -10
  within_peer_range: -5
gate:
  fraud_net: 60
  fraud_min_structural_types: 2
  review_net: 30
rollup: {noisy_or: true}
```
Rules: behaviour alone never yields FRAUD; structural types = {shared_device, common_sink, pass_through, sequence_cohort, burst}; `sequence_cohort` counts only with convergence.

## Result export (CLI)
`reports/result.json`: `{tx:[...], accounts:[...], groups:[...], evidence:[...], metrics:{...}, degraded:[...]}`; `reports/case_<group_id>.html`.
