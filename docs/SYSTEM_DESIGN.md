# TRACE-FX SYSTEM DESIGN

## 1. Problem
Financial fraud systems often operate as black boxes, making it difficult for analysts to understand why an account was flagged or why a legitimate-looking but subtly malicious account was missed. A single model score lacks the nuance required for defensive decision-making in a regulatory environment.

## 2. System Thesis
"Don't just detect the fraud. Show the evidence, and show why we didn't accuse the innocent."
The system must generate an explicit evidence ledger for every user-visible decision, ensuring that the ultimate explanation is structurally sound rather than generated post-hoc.

## 3. Architecture
TRACE-FX is an offline batch-processing system with causal temporal replay capabilities (not a real-time streaming engine).
The pipeline flows sequentially:
`CSV Input → Schema Validation → Behavioural Features → Behaviour Scorer → Typed Graph → Motifs (M1-M5) → Evidence Ledger → Precision Gate → Account/Group Rollup → Explanation → Result`

## 4. Data Contract
- **Required**: `tx_id`, `ts`, `payer_id`, `payee_id`, `amount`
- **Optional**: `tx_type`, `device_id`, `ip`, `merchant_id`, `item_id`, `channel`, `city`, `account_open_date`, `label`
Missing optional fields gracefully degrade the system (e.g., missing IP disables IP motifs).

## 5. Behavioural Model
The behavioural model provides *anomaly scoring*, not fraud probability.
- **Algorithm**: `IsolationForest` (default).
- **Output**: Score between 0 (normal) and 1 (highly anomalous).
- **Usage**: Used purely as one piece of evidence, never independently triggering a FRAUD decision. Uses only past-available data.

## 6. Graph
The graph represents evidence-relevant entity relationships, such as payer to payee, or account to device/IP.
It is built using `networkx.MultiGraph` and enforces "hub caps" to prevent shared infrastructure (e.g., a popular merchant, public Wi-Fi) from artificially linking disjoint accounts into massive components.

## 7. Motifs
Structural fraud patterns are detected via five motifs:
- **M1 (Shared Device)**: Multiple accounts using the same device with no prior legitimate relationship.
- **M2 (Common Sink)**: Multiple distinct payers funneling funds to a single destination rapidly.
- **M3 (Pass-through)**: Funds received and rapidly (>=80%) transferred onward.
- **M4 (Sequence Cohort)**: Accounts displaying suspiciously similar rare transaction sequences that also converge monetarily.
- **M5 (Burst)**: High-velocity activity significantly above the account's baseline.

## 8. Ledger
The central decision mechanism. It collects points based on evidence types:
- **Positive Evidence**: Motifs and behavioural anomalies.
- **Negative (Exculpatory) Evidence**: Repeat legitimate payees, known devices, long account tenure.
All explanations are derived directly from this ledger.

## 9. Gate
The precision gate determines the final status:
- **FRAUD**: Requires `net_points >= 60` AND `>= 2` independent structural motifs.
- **REVIEW**: Requires `net_points >= 30` OR a strong structural signal.
- **LEGIT**: Otherwise.

## 10. Rollup
Account risk is calculated using a noisy-OR formulation based on the ledger points. Groups are formed dynamically using connected components over *evidence relationships*, avoiding giant components formed by innocent shared infrastructure.

## 11. Causal Alert Time
The system explicitly avoids future information leakage. `alert_ts` is assigned based on the earliest timestamp at which the gate conditions (evidence + points) became definitively satisfied.

## 12. Evaluation
Evaluates system metrics such as precision, recall, F1, latency, and PR-AUC. A causality prefix-equivalence check verifies that re-running the system up to a partial checkpoint yields the same intermediate state as the full run.

## 13. UI
Built with Streamlit, the UI reads the frozen `Result` object and provides interactive exploration of the queue, decision state, evidence ledger, graph relationships, and system quality. It contains no raw fraud logic.

## 14. Failure/Degraded Modes
The pipeline fails soft. If optional inputs are missing or specific detectors fail, they are appended to the `degraded` capabilities report in the `Result` and the pipeline continues operating with whatever evidence is available.

## 15. Dataset Strategy
Primarily tested and validated via a synthetic data simulator that generates controlled seeds (`demo_small`, `seedA`, `seedB`, `seedC`) containing standard accounts, noisy shared infrastructure, and planted fraud rings.

## 16. Disclosure
Any external open-source models, libraries, or datasets utilized must be explicitly cited in `DISCLOSURE.md`. 

## 17. Limitations
- Offline batch processing only; not a live runtime application.
- GPU dependency is deliberately avoided for portability.
- Graph capabilities are limited to in-memory `networkx`.

## 18. What is Implemented
- Repository structure, contracts, and type definitions.
- Config validation, schema parsing, mock endpoints, and test foundations.

## 19. What is Not Implemented (To Be Done)
- Complete IsolatonForest feature engineering.
- Sophisticated graph scoring and advanced motif logic.
- Red-team evaluation, full UI polish, and production casefile generation.
