### (a) Definition of precision_fraud and recall_fraud in evaluate.py
```python
    # ----- Precision / account-level -----
    fraud_tx_ids = set(truth.get("is_fraud_tx_ids", []))
    ring_accounts = set()
    for ring in rings:
        if ring.get("type") == "R1":  # only R1 is expected FRAUD
            ring_accounts.update(ring.get("accounts", []))

    if not accs.empty and ring_accounts:
        pred_fraud_accs = set(accs[accs["label"] == "FRAUD"].index)
        pred_review_accs = set(accs[accs["label"] == "REVIEW"].index)

        tp_fraud = len(pred_fraud_accs & ring_accounts)
        fp_fraud = len(pred_fraud_accs - ring_accounts)
        precision_fraud = tp_fraud / max(len(pred_fraud_accs), 1)
        recall_fraud = tp_fraud / max(len(ring_accounts), 1)
```
Unit is account-level. Only R1 accounts are counted as true positives for FRAUD.

### (b) Accounts at FRAUD tier
**Account ID:** W9664
**In truth fraud set (R1):** False
**Net Points:** unknown
**Ledger:**

**Account ID:** W9028
**In truth fraud set (R1):** False
**Net Points:** unknown
**Ledger:**

**Account ID:** A15325
**In truth fraud set (R1):** False
**Net Points:** 71.0
**Ledger:**
- 25 | pass_through | +25 Pass-through: account A15325 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044498, T0044499.
- 25 | pass_through | +25 Pass-through: account A77233 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044497, T0044498.
- 25 | pass_through | +25 Pass-through: account A34431 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044499, T0044500.
- 10 | burst | +10 Burst activity: A15325 shows z=4.8 transaction spike within 1h window; supporting transactions: T0032234.
- 16 | behaviour_anomaly | +16.0 Behaviour anomaly score 0.80: unusual activity relative to account baseline and peers; most anomalous transactions: T0044499, T0032214, T0032213.
- -20 | repeat_payee_3plus | -20 Repeat payee: destination M0013 used 6 times before the suspicious window — likely known relationship; supporting transactions: T0032215, T0032216, T0032218.
- -10 | known_device_5plus | -10 Known device: device D70272 used 13 times — established device reduces suspicion; supporting transactions: T0032213, T0032217, T0032219.


### (c) Truth Ring Stats
**Ring 1 (R1)**: 10 members
- FRAUD: 0, REVIEW: 10, LEGIT: 0
- Max net points among members: 51.9
**Ring 2 (R1)**: 7 members
- FRAUD: 0, REVIEW: 7, LEGIT: 0
- Max net points among members: 58.9
**Ring 3 (R1)**: 5 members
- FRAUD: 0, REVIEW: 5, LEGIT: 0
- Max net points among members: 55.8
**Ring 4 (R2)**: 4 members
- FRAUD: 1, REVIEW: 3, LEGIT: 0
- Max net points among members: 71.0
**Ring 5 (R2)**: 4 members
- FRAUD: 0, REVIEW: 4, LEGIT: 0
- Max net points among members: 46.0

### (d) Conclusion
The metrics report `precision_fraud=0.0` and `recall_fraud=0.0` because `evaluate.py` strictly considers only 'R1' (Type 1) ring members as true positive targets for the FRAUD label. The 3 accounts reaching the FRAUD tier in seedA belong to different truth sets (likely isolated or non-R1 fraud) so they are counted as false positives for the specific R1 metric. Meanwhile, the actual R1 ring members did not accumulate the 60 net points required by the deterministic gate (they only reached the REVIEW tier). This represents a metric-definition artefact combined with conservative point thresholding: the system successfully detects the rings (ring_recall_full=5/5) but classifies their members as REVIEW rather than FRAUD, resulting in 0 precision/recall for the strict FRAUD vs R1 classification.