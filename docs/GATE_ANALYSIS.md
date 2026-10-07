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

        # precision@10: among top 10 by risk, how many are true fraud?
        top10 = accs.nlargest(10, "risk").index.tolist() if len(accs) >= 10 else accs.index.tolist()
        p_at_10 = len(set(top10) & ring_accounts) / max(len(top10), 1)

        top50 = accs.nlargest(50, "risk").index.tolist() if len(accs) >= 50 else accs.index.tolist()
        p_at_50 = len(set(top50) & ring_accounts) / max(len(top50), 1)

        # PR-AUC approximation
        all_risks = accs["risk"].values
        all_labels = accs.index.map(lambda x: 1 if x in ring_accounts else 0).values
        pr_auc = _approx_pr_auc(all_risks, all_labels)
```

### (b) Truth Ring Stats
**Seed: seedA**
- Ring 1 (R1, expected FRAUD): 10 members (FRAUD: 0, REVIEW: 10, LEGIT: 0)
  - A95998: max net points 13.4, 2 structural types, motifs: behaviour_anomaly, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A18551: max net points 38.4, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A35280: max net points 36.2, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A63297: max net points 31.0, 3 structural types, motifs: behaviour_anomaly, shared_device, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A49586: max net points 51.9, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, common_sink, repeat_payee_3plus, burst
  - A55888: max net points 37.5, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A47740: max net points 40.0, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A41327: max net points 41.9, 2 structural types, motifs: behaviour_anomaly, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A15218: max net points 12.2, 2 structural types, motifs: behaviour_anomaly, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A12392: max net points 36.7, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
- Ring 2 (R1, expected FRAUD): 7 members (FRAUD: 0, REVIEW: 7, LEGIT: 0)
  - A64319: max net points 35.9, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A94803: max net points 58.9, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A16879: max net points 57.7, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A23151: max net points 12.3, 2 structural types, motifs: behaviour_anomaly, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A67546: max net points 31.5, 3 structural types, motifs: behaviour_anomaly, shared_device, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A85318: max net points 48.9, 3 structural types, motifs: behaviour_anomaly, shared_device, known_device_5plus, common_sink, repeat_payee_3plus, burst
  - A29448: max net points 58.0, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
- Ring 3 (R1, expected FRAUD): 5 members (FRAUD: 0, REVIEW: 5, LEGIT: 0)
  - A24578: max net points 55.8, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A69881: max net points 13.9, 2 structural types, motifs: behaviour_anomaly, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A39346: max net points 49.2, 3 structural types, motifs: behaviour_anomaly, shared_device, known_device_5plus, common_sink, repeat_payee_3plus, burst
  - A54884: max net points 20.0, 2 structural types, motifs: behaviour_anomaly, shared_device, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus
  - A39595: max net points 30.9, 3 structural types, motifs: behaviour_anomaly, shared_device, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
- Ring 4 (R2, expected REVIEW): 4 members (FRAUD: 1, REVIEW: 3, LEGIT: 0)
- Ring 5 (R2, expected REVIEW): 4 members (FRAUD: 0, REVIEW: 4, LEGIT: 0)

**Seed: seedB**
- Ring 1 (R1, expected FRAUD): 10 members (FRAUD: 1, REVIEW: 9, LEGIT: 0)
  - A85468: max net points 53.1, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, common_sink, repeat_payee_3plus, burst
  - A83624: max net points 38.6, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A17431: max net points 38.8, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A16134: max net points 37.9, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A33204: max net points 52.9, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, common_sink, repeat_payee_3plus, burst
  - A69660: max net points 14.9, 2 structural types, motifs: behaviour_anomaly, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A47188: max net points 69.9, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A55281: max net points 29.0, 2 structural types, motifs: known_device_5plus, behaviour_anomaly, common_sink, repeat_payee_3plus, burst
  - A82587: max net points 13.9, 2 structural types, motifs: behaviour_anomaly, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A30261: max net points 38.2, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
- Ring 2 (R1, expected FRAUD): 7 members (FRAUD: 5, REVIEW: 2, LEGIT: 0)
  - A76446: max net points 60.0, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A94131: max net points 70.0, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A99311: max net points 72.9, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, common_sink, repeat_payee_3plus, burst
  - A77660: max net points 82.1, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, common_sink, repeat_payee_3plus, burst
  - A52945: max net points 48.7, 3 structural types, motifs: behaviour_anomaly, shared_device, known_device_5plus, common_sink, repeat_payee_3plus, burst
  - A96936: max net points 70.8, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, common_sink, repeat_payee_3plus, burst
  - A38187: max net points 57.7, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
- Ring 3 (R1, expected FRAUD): 5 members (FRAUD: 0, REVIEW: 5, LEGIT: 0)
  - A61546: max net points 52.1, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, common_sink, repeat_payee_3plus, burst
  - A62568: max net points 44.3, 3 structural types, motifs: behaviour_anomaly, shared_device, known_device_5plus, common_sink, repeat_payee_3plus, burst
  - A39484: max net points 34.9, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A37366: max net points 54.7, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A90378: max net points 55.4, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
- Ring 4 (R2, expected REVIEW): 4 members (FRAUD: 1, REVIEW: 3, LEGIT: 0)
- Ring 5 (R2, expected REVIEW): 4 members (FRAUD: 0, REVIEW: 4, LEGIT: 0)

**Seed: seedC**
- Ring 1 (R1, expected FRAUD): 10 members (FRAUD: 2, REVIEW: 8, LEGIT: 0)
  - A78652: max net points 39.6, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A72440: max net points 38.5, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A57390: max net points 52.5, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, common_sink, repeat_payee_3plus, burst
  - A91923: max net points 37.9, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A61888: max net points 38.7, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A24862: max net points 45.0, 2 structural types, motifs: behaviour_anomaly, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A80372: max net points 28.0, 2 structural types, motifs: known_device_5plus, behaviour_anomaly, common_sink, repeat_payee_3plus, burst
  - A69686: max net points 94.5, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A47421: max net points 53.7, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, common_sink, repeat_payee_3plus, burst
  - A72608: max net points 63.1, 3 structural types, motifs: behaviour_anomaly, shared_device, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
- Ring 2 (R1, expected FRAUD): 7 members (FRAUD: 1, REVIEW: 6, LEGIT: 0)
  - A38774: max net points 58.4, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A92746: max net points 58.6, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A44328: max net points 87.8, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A92238: max net points 39.8, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A10732: max net points 14.2, 2 structural types, motifs: behaviour_anomaly, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A64302: max net points 58.8, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A23207: max net points 57.3, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
- Ring 3 (R1, expected FRAUD): 5 members (FRAUD: 2, REVIEW: 3, LEGIT: 0)
  - A91681: max net points 32.7, 3 structural types, motifs: behaviour_anomaly, shared_device, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A17195: max net points 71.5, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, common_sink, repeat_payee_3plus, burst
  - A25508: max net points 35.8, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A69686: max net points 94.5, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A63566: max net points 57.9, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
- Ring 4 (R2, expected REVIEW): 4 members (FRAUD: 0, REVIEW: 4, LEGIT: 0)
- Ring 5 (R2, expected REVIEW): 4 members (FRAUD: 2, REVIEW: 2, LEGIT: 0)
- Ring 6 (R3, expected undetected): 4 members (FRAUD: 2, REVIEW: 2, LEGIT: 0)

**Seed: demo_small**
- Ring 1 (R1, expected FRAUD): 10 members (FRAUD: 3, REVIEW: 7, LEGIT: 0)
  - A56725: max net points 15.0, 2 structural types, motifs: behaviour_anomaly, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A52960: max net points 59.6, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, burst
  - A93718: max net points 37.9, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A88769: max net points 77.5, 2 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink
  - A27489: max net points 3.4, 1 structural types, motifs: known_device_5plus, behaviour_anomaly, tenure_over_1y, common_sink, repeat_payee_3plus
  - A57422: max net points 44.8, 2 structural types, motifs: behaviour_anomaly, known_device_5plus, tenure_over_1y, common_sink, repeat_payee_3plus, burst
  - A42885: max net points 88.1, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, burst
  - A52147: max net points 59.7, 3 structural types, motifs: behaviour_anomaly, known_device_5plus, pass_through, tenure_over_1y, common_sink, burst
  - A78201: max net points 79.0, 4 structural types, motifs: behaviour_anomaly, shared_device, pass_through, known_device_5plus, tenure_over_1y, common_sink, burst
  - A65733: max net points 48.7, 2 structural types, motifs: common_sink, behaviour_anomaly, known_device_5plus, burst
- Ring 2 (R2, expected REVIEW): 4 members (FRAUD: 0, REVIEW: 4, LEGIT: 0)

### (c) FRAUD-tier Accounts Ledgers
**Seed: seedA**
- **Account:** W9028 | **Truth:** none
- **Account:** W9664 | **Truth:** none
- **Account:** A15325 | **Truth:** Ring R2
  > 25.0 | pass_through | +25 Pass-through: account A15325 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044498, T0044499.
  > 25.0 | pass_through | +25 Pass-through: account A77233 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044497, T0044498.
  > 25.0 | pass_through | +25 Pass-through: account A34431 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044499, T0044500.
  > 10.0 | burst | +10 Burst activity: A15325 shows z=4.8 transaction spike within 1h window; supporting transactions: T0032234.
  > 16.0 | behaviour_anomaly | +16.0 Behaviour anomaly score 0.80: unusual activity relative to account baseline and peers; most anomalous transactions: T0044499, T0032214, T0032213.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0013 used 6 times before the suspicious window — likely known relationship; supporting transactions: T0032215, T0032216, T0032218.
  > -10.0 | known_device_5plus | -10 Known device: device D70272 used 13 times — established device reduces suspicion; supporting transactions: T0032213, T0032217, T0032219.
**Seed: seedB**
- **Account:** W9708 | **Truth:** none
- **Account:** W9448 | **Truth:** none
- **Account:** W9461 | **Truth:** none
- **Account:** A18668 | **Truth:** Ring R2
  > 30.0 | common_sink | +30 Common sink: 17 distinct accounts paid wallet/payee M0007 within 24h; supporting transactions: T0021585, T0028099, T0021294.
  > 25.0 | pass_through | +25 Pass-through: account A18668 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044191, T0044192.
  > 25.0 | pass_through | +25 Pass-through: account A50865 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044192, T0044193.
  > 25.0 | pass_through | +25 Pass-through: account A45392 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044190, T0044191.
  > 14.8 | behaviour_anomaly | +14.8 Behaviour anomaly score 0.74: unusual activity relative to account baseline and peers; most anomalous transactions: T0032546, T0044192, T0032547.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0007 used 5 times before the suspicious window — likely known relationship; supporting transactions: T0032546, T0032547, T0032550.
  > -10.0 | known_device_5plus | -10 Known device: device D59400 used 22 times — established device reduces suspicion; supporting transactions: T0032546, T0032547, T0032548.
- **Account:** A77660 | **Truth:** Ring R1
  > 30.0 | common_sink | +30 Common sink: 4 distinct accounts paid wallet/payee W0026 within 24h; supporting transactions: T0029993, T0013648, T0020895.
  > 30.0 | common_sink | +30 Common sink: 7 distinct accounts paid wallet/payee W9448 within 24h; supporting transactions: T0044117, T0044106, T0044122.
  > 25.0 | pass_through | +25 Pass-through: account A77660 received funds then forwarded 94% onward within 30 min; supporting transactions: T0044103, T0044104, T0044105.
  > 10.0 | burst | +10 Burst activity: A77660 shows z=4.5 transaction spike within 1h window; supporting transactions: T0044106.
  > 17.1 | behaviour_anomaly | +17.1 Behaviour anomaly score 0.85: unusual activity relative to account baseline and peers; most anomalous transactions: T0044106, T0044063, T0020894.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0025 used 5 times before the suspicious window — likely known relationship; supporting transactions: T0020896, T0020900, T0020905.
  > -10.0 | known_device_5plus | -10 Known device: device D48828 used 17 times — established device reduces suspicion; supporting transactions: T0020894, T0020896, T0044058.
- **Account:** A99311 | **Truth:** Ring R1
  > 20.0 | shared_device | +20 Shared device D74404 linked 5 accounts with no prior payer/payee relationship; supporting transactions: T0044113, T0044108, T0044117.
  > 30.0 | common_sink | +30 Common sink: 7 distinct accounts paid wallet/payee W9448 within 24h; supporting transactions: T0044117, T0044106, T0044122.
  > 25.0 | pass_through | +25 Pass-through: account A99311 received funds then forwarded 103% onward within 30 min; supporting transactions: T0044098, T0044099, T0044100.
  > 10.0 | burst | +10 Burst activity: A99311 shows z=4.4 transaction spike within 1h window; supporting transactions: T0044102.
  > 17.9 | behaviour_anomaly | +17.9 Behaviour anomaly score 0.89: unusual activity relative to account baseline and peers; most anomalous transactions: T0044102, T0044056, T0044099.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0022 used 5 times before the suspicious window — likely known relationship; supporting transactions: T0005467, T0005474, T0005478.
  > -10.0 | known_device_5plus | -10 Known device: device D83279 used 15 times — established device reduces suspicion; supporting transactions: T0044056, T0005465, T0044051.
- **Account:** A96936 | **Truth:** Ring R1
  > 20.0 | shared_device | +20 Shared device D74404 linked 5 accounts with no prior payer/payee relationship; supporting transactions: T0044113, T0044108, T0044117.
  > 30.0 | common_sink | +30 Common sink: 7 distinct accounts paid wallet/payee W9448 within 24h; supporting transactions: T0044117, T0044106, T0044122.
  > 25.0 | pass_through | +25 Pass-through: account A96936 received funds then forwarded 120% onward within 30 min; supporting transactions: T0044112, T0044113, T0044117.
  > 10.0 | burst | +10 Burst activity: A96936 shows z=3.6 transaction spike within 1h window; supporting transactions: T0044115.
  > 15.8 | behaviour_anomaly | +15.8 Behaviour anomaly score 0.79: unusual activity relative to account baseline and peers; most anomalous transactions: T0044117, T0044113, T0044077.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0015 used 7 times before the suspicious window — likely known relationship; supporting transactions: T0014376, T0014377, T0014378.
  > -10.0 | known_device_5plus | -10 Known device: device D12606 used 21 times — established device reduces suspicion; supporting transactions: T0044077, T0044078, T0014376.
- **Account:** A94131 | **Truth:** Ring R1
  > 30.0 | common_sink | +30 Common sink: 5 distinct accounts paid wallet/payee W0021 within 24h; supporting transactions: T0005364, T0008076, T0013559.
  > 30.0 | common_sink | +30 Common sink: 7 distinct accounts paid wallet/payee W9448 within 24h; supporting transactions: T0044117, T0044106, T0044122.
  > 25.0 | pass_through | +25 Pass-through: account A94131 received funds then forwarded 103% onward within 30 min; supporting transactions: T0044089, T0044095, T0044090.
  > 10.0 | burst | +10 Burst activity: A94131 shows z=3.6 transaction spike within 1h window; supporting transactions: T0044096, T0044097.
  > 20.0 | behaviour_anomaly | +20.0 Behaviour anomaly score 1.00: unusual activity relative to account baseline and peers; most anomalous transactions: T0044097, T0044096, T0044094.
  > -15.0 | tenure_over_1y | -15 Account tenure 1071 days (>365 days): established account reduces suspicion; sample transactions: T0013556, T0044046.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0008 used 5 times before the suspicious window — likely known relationship; supporting transactions: T0013557, T0013566, T0013567.
  > -10.0 | known_device_5plus | -10 Known device: device D60014 used 40 times — established device reduces suspicion; supporting transactions: T0013556, T0044046, T0013557.
- **Account:** A47188 | **Truth:** Ring R1
  > 30.0 | common_sink | +30 Common sink: 4 distinct accounts paid wallet/payee W0007 within 24h; supporting transactions: T0031429, T0032886, T0008966.
  > 30.0 | common_sink | +30 Common sink: 10 distinct accounts paid wallet/payee W9461 within 24h; supporting transactions: T0043992, T0044028, T0043970.
  > 25.0 | pass_through | +25 Pass-through: account A47188 received funds then forwarded 120% onward within 30 min; supporting transactions: T0044000, T0044002, T0044006.
  > 10.0 | burst | +10 Burst activity: A47188 shows z=4.5 transaction spike within 1h window; supporting transactions: T0044004, T0044005.
  > 19.9 | behaviour_anomaly | +19.9 Behaviour anomaly score 1.00: unusual activity relative to account baseline and peers; most anomalous transactions: T0044006, T0044002, T0044004.
  > -15.0 | tenure_over_1y | -15 Account tenure 1496 days (>365 days): established account reduces suspicion; sample transactions: T0031429, T0031430.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0016 used 5 times before the suspicious window — likely known relationship; supporting transactions: T0031433, T0031435, T0031445.
  > -10.0 | known_device_5plus | -10 Known device: device D13479 used 26 times — established device reduces suspicion; supporting transactions: T0031430, T0031432, T0043945.
- **Account:** A76446 | **Truth:** Ring R1
  > 20.0 | shared_device | +20 Shared device D74404 linked 5 accounts with no prior payer/payee relationship; supporting transactions: T0044113, T0044108, T0044117.
  > 30.0 | common_sink | +30 Common sink: 7 distinct accounts paid wallet/payee W9448 within 24h; supporting transactions: T0044117, T0044106, T0044122.
  > 25.0 | pass_through | +25 Pass-through: account A76446 received funds then forwarded 128% onward within 30 min; supporting transactions: T0044083, T0044086, T0044084.
  > 10.0 | burst | +10 Burst activity: A76446 shows z=4.5 transaction spike within 1h window; supporting transactions: T0044087, T0044088.
  > 20.0 | behaviour_anomaly | +20.0 Behaviour anomaly score 1.00: unusual activity relative to account baseline and peers; most anomalous transactions: T0044088, T0044085, T0044086.
  > -15.0 | tenure_over_1y | -15 Account tenure 848 days (>365 days): established account reduces suspicion; sample transactions: T0034583, T0044034.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0012 used 5 times before the suspicious window — likely known relationship; supporting transactions: T0034583, T0034587, T0034588.
  > -10.0 | known_device_5plus | -10 Known device: device D10564 used 19 times — established device reduces suspicion; supporting transactions: T0034583, T0034584, T0044037.
**Seed: seedC**
- **Account:** A69509 | **Truth:** Ring R3
  > 25.0 | pass_through | +25 Pass-through: account A66979 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044385, T0044386.
  > 25.0 | pass_through | +25 Pass-through: account A66979 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044389, T0044390.
  > 25.0 | pass_through | +25 Pass-through: account A66979 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044393, T0044394.
  > 25.0 | pass_through | +25 Pass-through: account A31621 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044387, T0044388.
  > 25.0 | pass_through | +25 Pass-through: account A31621 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044391, T0044392.
  > 25.0 | pass_through | +25 Pass-through: account A31621 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044395, T0044396.
  > 10.0 | burst | +10 Burst activity: A69509 shows z=4.1 transaction spike within 1h window; supporting transactions: T0006047.
  > 16.6 | behaviour_anomaly | +16.6 Behaviour anomaly score 0.83: unusual activity relative to account baseline and peers; most anomalous transactions: T0044385, T0044389, T0044393.
  > -15.0 | tenure_over_1y | -15 Account tenure 1650 days (>365 days): established account reduces suspicion; sample transactions: T0006040, T0006041.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0006 used 5 times before the suspicious window — likely known relationship; supporting transactions: T0006041, T0006047, T0006049.
  > -10.0 | known_device_5plus | -10 Known device: device D49896 used 10 times — established device reduces suspicion; supporting transactions: T0006044, T0006045, T0006046.
  > -10.0 | amount_within_p95 | -10 Transaction amounts within account p95 (max ₹30000 vs p95 ₹30000): no unusual amount spike; transactions: T0044385, T0044389.
- **Account:** A60432 | **Truth:** Ring R3
  > 25.0 | pass_through | +25 Pass-through: account A60432 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044386, T0044387.
  > 25.0 | pass_through | +25 Pass-through: account A60432 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044390, T0044391.
  > 25.0 | pass_through | +25 Pass-through: account A60432 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044394, T0044395.
  > 25.0 | pass_through | +25 Pass-through: account A66979 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044385, T0044386.
  > 25.0 | pass_through | +25 Pass-through: account A66979 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044389, T0044390.
  > 25.0 | pass_through | +25 Pass-through: account A66979 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044393, T0044394.
  > 25.0 | pass_through | +25 Pass-through: account A31621 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044387, T0044388.
  > 25.0 | pass_through | +25 Pass-through: account A31621 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044391, T0044392.
  > 25.0 | pass_through | +25 Pass-through: account A31621 received funds then forwarded 100% onward within 30 min; supporting transactions: T0044395, T0044396.
  > 10.0 | burst | +10 Burst activity: A60432 shows z=3.2 transaction spike within 1h window; supporting transactions: T0040002, T0040011.
  > 18.0 | behaviour_anomaly | +18.0 Behaviour anomaly score 0.90: unusual activity relative to account baseline and peers; most anomalous transactions: T0044387, T0044391, T0044395.
  > -15.0 | tenure_over_1y | -15 Account tenure 1135 days (>365 days): established account reduces suspicion; sample transactions: T0039996, T0039997.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0005 used 7 times before the suspicious window — likely known relationship; supporting transactions: T0039997, T0039998, T0040001.
  > -10.0 | known_device_5plus | -10 Known device: device D43489 used 22 times — established device reduces suspicion; supporting transactions: T0039996, T0039997, T0039998.
  > -10.0 | amount_within_p95 | -10 Transaction amounts within account p95 (max ₹30000 vs p95 ₹30000): no unusual amount spike; transactions: T0044387, T0044391.
- **Account:** W9214 | **Truth:** none
- **Account:** W9684 | **Truth:** none
- **Account:** W9554 | **Truth:** none
- **Account:** A69686 | **Truth:** Ring R1
  > 30.0 | common_sink | +30 Common sink: 5 distinct accounts paid wallet/payee W9684 within 24h; supporting transactions: T0044358, T0044364, T0044368.
  > 30.0 | common_sink | +30 Common sink: 10 distinct accounts paid wallet/payee W9214 within 24h; supporting transactions: T0044180, T0044143, T0044165.
  > 25.0 | pass_through | +25 Pass-through: account A69686 received funds then forwarded 104% onward within 30 min; supporting transactions: T0044365, T0044366, T0044368.
  > 25.0 | pass_through | +25 Pass-through: account A69686 received funds then forwarded 126% onward within 30 min; supporting transactions: T0044175, T0044176, T0044178.
  > 10.0 | burst | +10 Burst activity: A69686 shows z=4.8 transaction spike within 1h window; supporting transactions: T0044180, T0044179.
  > 19.5 | behaviour_anomaly | +19.5 Behaviour anomaly score 0.98: unusual activity relative to account baseline and peers; most anomalous transactions: T0044180, T0044368, T0044176.
  > -15.0 | tenure_over_1y | -15 Account tenure 1553 days (>365 days): established account reduces suspicion; sample transactions: T0044336, T0036999.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0004 used 12 times before the suspicious window — likely known relationship; supporting transactions: T0037000, T0037001, T0037002.
  > -10.0 | known_device_5plus | -10 Known device: device D73720 used 49 times — established device reduces suspicion; supporting transactions: T0044336, T0036999, T0044327.
- **Account:** A44328 | **Truth:** Ring R1
  > 20.0 | shared_device | +20 Shared device D74532 linked 5 accounts with no prior payer/payee relationship; supporting transactions: T0044263, T0044265, T0044264.
  > 30.0 | common_sink | +30 Common sink: 17 distinct accounts paid wallet/payee M0006 within 24h; supporting transactions: T0026873, T0015637, T0031145.
  > 30.0 | common_sink | +30 Common sink: 7 distinct accounts paid wallet/payee W9554 within 24h; supporting transactions: T0044272, T0044284, T0044298.
  > 25.0 | pass_through | +25 Pass-through: account A44328 received funds then forwarded 98% onward within 30 min; supporting transactions: T0044273, T0044276, T0044277.
  > 10.0 | burst | +10 Burst activity: A44328 shows z=4.0 transaction spike within 1h window; supporting transactions: T0044278.
  > 17.8 | behaviour_anomaly | +17.8 Behaviour anomaly score 0.89: unusual activity relative to account baseline and peers; most anomalous transactions: T0044278, T0033494, T0044276.
  > -15.0 | tenure_over_1y | -15 Account tenure 385 days (>365 days): established account reduces suspicion; sample transactions: T0033493, T0033494.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0006 used 8 times before the suspicious window — likely known relationship; supporting transactions: T0033493, T0033496, T0033499.
  > -10.0 | known_device_5plus | -10 Known device: device D78114 used 14 times — established device reduces suspicion; supporting transactions: T0033494, T0033496, T0033498.
- **Account:** A61552 | **Truth:** Ring R2
  > 20.0 | shared_device | +20 Shared device D41826 linked 2 accounts with no prior payer/payee relationship; supporting transactions: T0005131, T0026502, T0026503.
  > 25.0 | pass_through | +25 Pass-through: account A45782 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044380, T0044381.
  > 25.0 | pass_through | +25 Pass-through: account A61552 received funds then forwarded 87% onward within 30 min; supporting transactions: T0044381, T0044382, T0005140.
  > 25.0 | pass_through | +25 Pass-through: account A90045 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044382, T0044383.
  > 10.0 | burst | +10 Burst activity: A61552 shows z=3.3 transaction spike within 1h window; supporting transactions: T0045097.
  > 17.4 | behaviour_anomaly | +17.4 Behaviour anomaly score 0.87: unusual activity relative to account baseline and peers; most anomalous transactions: T0044382, T0005130, T0045098.
  > -15.0 | tenure_over_1y | -15 Account tenure 820 days (>365 days): established account reduces suspicion; sample transactions: T0005130, T0005131.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0001 used 3 times before the suspicious window — likely known relationship; supporting transactions: T0005130, T0005137, T0005141.
  > -10.0 | known_device_5plus | -10 Known device: device D69697 used 12 times — established device reduces suspicion; supporting transactions: T0005130, T0045098, T0005132.
- **Account:** A17195 | **Truth:** Ring R1
  > 20.0 | shared_device | +20 Shared device D47727 linked 3 accounts with no prior payer/payee relationship; supporting transactions: T0044354, T0044356, T0044353.
  > 30.0 | common_sink | +30 Common sink: 5 distinct accounts paid wallet/payee W9684 within 24h; supporting transactions: T0044358, T0044364, T0044368.
  > 25.0 | pass_through | +25 Pass-through: account A17195 received funds then forwarded 130% onward within 30 min; supporting transactions: T0044352, T0044354, T0044356.
  > 10.0 | burst | +10 Burst activity: A17195 shows z=4.2 transaction spike within 1h window; supporting transactions: T0044357, T0044358.
  > 16.5 | behaviour_anomaly | +16.5 Behaviour anomaly score 0.83: unusual activity relative to account baseline and peers; most anomalous transactions: T0044358, T0044317, T0044318.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0029 used 6 times before the suspicious window — likely known relationship; supporting transactions: T0021340, T0021341, T0021343.
  > -10.0 | known_device_5plus | -10 Known device: device D92862 used 18 times — established device reduces suspicion; supporting transactions: T0044317, T0021329, T0044319.
- **Account:** A11156 | **Truth:** Ring R2
  > 30.0 | common_sink | +30 Common sink: 4 distinct accounts paid wallet/payee W0022 within 24h; supporting transactions: T0017580, T0032612, T0021893.
  > 25.0 | pass_through | +25 Pass-through: account A90045 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044382, T0044383.
  > 25.0 | pass_through | +25 Pass-through: account A11156 received funds then forwarded 85% onward within 30 min; supporting transactions: T0044383, T0044384.
  > 16.6 | behaviour_anomaly | +16.6 Behaviour anomaly score 0.83: unusual activity relative to account baseline and peers; most anomalous transactions: T0044384, T0011123, T0011124.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0011 used 4 times before the suspicious window — likely known relationship; supporting transactions: T0011126, T0011133, T0011134.
  > -10.0 | known_device_5plus | -10 Known device: device D90372 used 10 times — established device reduces suspicion; supporting transactions: T0011123, T0011125, T0011126.
- **Account:** A72608 | **Truth:** Ring R1
  > 20.0 | shared_device | +20 Shared device D32998 linked 2 accounts with no prior payer/payee relationship; supporting transactions: T0044131, T0003858, T0042319.
  > 30.0 | common_sink | +30 Common sink: 6 distinct accounts paid wallet/payee W0017 within 24h; supporting transactions: T0014717, T0035704, T0026475.
  > 30.0 | common_sink | +30 Common sink: 10 distinct accounts paid wallet/payee W9214 within 24h; supporting transactions: T0044180, T0044143, T0044165.
  > 10.0 | burst | +10 Burst activity: A72608 shows z=3.8 transaction spike within 1h window; supporting transactions: T0044194.
  > 18.1 | behaviour_anomaly | +18.1 Behaviour anomaly score 0.90: unusual activity relative to account baseline and peers; most anomalous transactions: T0044195, T0044129, T0044190.
  > -15.0 | tenure_over_1y | -15 Account tenure 1530 days (>365 days): established account reduces suspicion; sample transactions: T0042318, T0044131.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0016 used 6 times before the suspicious window — likely known relationship; supporting transactions: T0042320, T0042321, T0042322.
  > -10.0 | known_device_5plus | -10 Known device: device D38693 used 19 times — established device reduces suspicion; supporting transactions: T0042318, T0042320, T0044129.
**Seed: demo_small**
- **Account:** W9925 | **Truth:** none
- **Account:** A42885 | **Truth:** Ring R1
  > 30.0 | common_sink | +30 Common sink: 4 distinct accounts paid wallet/payee M0019 within 24h; supporting transactions: T0000319, T0004415, T0000289.
  > 30.0 | common_sink | +30 Common sink: 10 distinct accounts paid wallet/payee W9925 within 24h; supporting transactions: T0004903, T0004899, T0004865.
  > 25.0 | pass_through | +25 Pass-through: account A42885 received funds then forwarded 93% onward within 30 min; supporting transactions: T0004889, T0004890, T0004891.
  > 10.0 | burst | +10 Burst activity: A42885 shows z=3.1 transaction spike within 1h window; supporting transactions: T0004893.
  > 18.1 | behaviour_anomaly | +18.1 Behaviour anomaly score 0.91: unusual activity relative to account baseline and peers; most anomalous transactions: T0004893, T0004891, T0000790.
  > -15.0 | tenure_over_1y | -15 Account tenure 1433 days (>365 days): established account reduces suspicion; sample transactions: T0000789, T0000790.
  > -10.0 | known_device_5plus | -10 Known device: device D41744 used 10 times — established device reduces suspicion; supporting transactions: T0000789, T0004823, T0004821.
- **Account:** A78201 | **Truth:** Ring R1
  > 20.0 | shared_device | +20 Shared device D58937 linked 4 accounts with no prior payer/payee relationship; supporting transactions: T0004918, T0004919, T0004917.
  > 30.0 | common_sink | +30 Common sink: 10 distinct accounts paid wallet/payee W9925 within 24h; supporting transactions: T0004903, T0004899, T0004865.
  > 25.0 | pass_through | +25 Pass-through: account A78201 received funds then forwarded 103% onward within 30 min; supporting transactions: T0004900, T0004902, T0004901.
  > 10.0 | burst | +10 Burst activity: A78201 shows z=3.4 transaction spike within 1h window; supporting transactions: T0004903.
  > 19.0 | behaviour_anomaly | +19.0 Behaviour anomaly score 0.95: unusual activity relative to account baseline and peers; most anomalous transactions: T0004903, T0004373, T0004920.
  > -15.0 | tenure_over_1y | -15 Account tenure 845 days (>365 days): established account reduces suspicion; sample transactions: T0004365, T0004920.
  > -10.0 | known_device_5plus | -10 Known device: device D20908 used 18 times — established device reduces suspicion; supporting transactions: T0004365, T0004842, T0004366.
- **Account:** A88769 | **Truth:** Ring R1
  > 30.0 | common_sink | +30 Common sink: 4 distinct accounts paid wallet/payee W0000 within 24h; supporting transactions: T0003040, T0003255, T0001973.
  > 30.0 | common_sink | +30 Common sink: 10 distinct accounts paid wallet/payee W9925 within 24h; supporting transactions: T0004903, T0004899, T0004865.
  > 25.0 | pass_through | +25 Pass-through: account A88769 received funds then forwarded 106% onward within 30 min; supporting transactions: T0004871, T0004872, T0004873.
  > 17.5 | behaviour_anomaly | +17.5 Behaviour anomaly score 0.88: unusual activity relative to account baseline and peers; most anomalous transactions: T0004877, T0004872, T0003564.
  > -15.0 | tenure_over_1y | -15 Account tenure 1698 days (>365 days): established account reduces suspicion; sample transactions: T0003561, T0004802.
  > -10.0 | known_device_5plus | -10 Known device: device D95453 used 6 times — established device reduces suspicion; supporting transactions: T0003561, T0004802, T0003562.
- **Account:** A63219 | **Truth:** Hard Negative
  > 30.0 | common_sink | +30 Common sink: 9 distinct accounts paid wallet/payee M0021 within 24h; supporting transactions: T0001446, T0003566, T0002306.
  > 30.0 | common_sink | +30 Common sink: 5 distinct accounts paid wallet/payee M0003 within 24h; supporting transactions: T0000488, T0003240, T0002054.
  > 30.0 | common_sink | +30 Common sink: 4 distinct accounts paid wallet/payee W0010 within 24h; supporting transactions: T0000492, T0004455, T0001993.
  > 10.0 | burst | +10 Burst activity: A63219 shows z=3.3 transaction spike within 1h window; supporting transactions: T0005094.
  > 11.9 | behaviour_anomaly | +11.9 Behaviour anomaly score 0.59: unusual activity relative to account baseline and peers; most anomalous transactions: T0000501, T0000502, T0000500.
  > -15.0 | tenure_over_1y | -15 Account tenure 1243 days (>365 days): established account reduces suspicion; sample transactions: T0000488, T0000489.
  > -20.0 | repeat_payee_3plus | -20 Repeat payee: destination M0003 used 5 times before the suspicious window — likely known relationship; supporting transactions: T0000488, T0005092, T0005093.
  > -10.0 | known_device_5plus | -10 Known device: device D11615 used 18 times — established device reduces suspicion; supporting transactions: T0000488, T0000489, T0000490.

### (d) Conclusion
R1 members blocked from FRAUD tier cause distribution:
- Blocked by net_points < 60: 62
- Blocked by structural types < 2: 1

Conclusion: R1 members fail to reach the FRAUD tier primarily because they do not accumulate enough net points (often hitting ~50 points, below the 60 threshold) despite triggering the required structural motifs. This is a genuine threshold issue combined with a strict metric-definition artefact.