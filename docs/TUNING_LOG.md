# Tuning Log and Guardrail Decisions

## Baseline Reality: 50 points vs 60 threshold
Our gate analysis demonstrates that R1 ring members trigger the required structural motifs and accrue net points, typically maxing out around 50 points. However, the `config.yaml` gate for `fraud_net` is strictly set to 60. As a result, genuine synthetic fraud groups are appropriately flagged for attention but fall into the `REVIEW` tier rather than the `FRAUD` tier.

## Guardrail Decision: Refuse to overtune
In alignment with strict engineering principles and architecture locks, we refuse to "fix" the scoring simply to make the metric look artificially successful. We will not change `config.yaml`, bypass the precision block, or hard-code threshold adjustments to force R1 members into the `FRAUD` category. We document reality exactly as the deterministic engine outputs it.

## Expected Metrics
Because of the strict R1-only definition for `tp_fraud` combined with the 60 point gate, `precision_fraud` will remain ~0.0 on the strict metric. This occurs because R1 members correctly land in REVIEW instead of FRAUD. Real-world users would adjust the `fraud_net` threshold downward in `config.yaml` based on local operational capacity, but we will leave it at 60 to maintain strict architectural lock.
