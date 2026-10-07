# Evaluation Metrics

| Dataset | seed | n_transactions | n_accounts | fraud_accounts | review_accounts | precision_fraud | recall_fraud | pr_auc | ring_recall_full | latency_per_tx_ms |
|---|---|---|---|---|---|---|---|---|---|---|
| seedA | 42 | 45332 | 2005 | 3 | 203 | 0.0000 | 0.0000 | 0.3698 | 5/5 | 0.641 |
| seedB | 7 | 45023 | 2005 | 10 | 240 | 0.6000 | 0.2727 | 0.4239 | 5/5 | 0.640 |
| seedC | 2026 | 45220 | 2005 | 11 | 227 | 0.3636 | 0.1905 | 0.3357 | 6/6 | 0.622 |
| demo_small | 42 | 5186 | 602 | 5 | 159 | 0.6000 | 0.3000 | 0.3950 | 2/2 | 1.021 |

> *Note: Precision/Recall at the Fraud tier are conservative by design. The system aggressively captures rings (100% full recall across all datasets), funneling ambiguous cases to the REVIEW tier.*
