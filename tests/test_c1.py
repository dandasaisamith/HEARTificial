import pandas as pd
from tracefx import evaluate

def test_additive_metrics_anyring(tmp_path):
    # Mock evaluate outputs for testing metric computation
    csv_path = tmp_path / "mock.csv"
    csv_path.write_text("tx_id,ts,payer_id,payee_id,amount\nT1,2025-01-01T00:00:00Z,U1,S1,10\n")
    truth_path = tmp_path / "truth_mock.json"
    truth_path.write_text('{"rings": [{"type": "R2", "accounts": ["U1", "U2"]}], "hard_negatives": [{"accounts": ["U3"]}]}')

    class MockPipelineResult:
        def __init__(self):
            self.accounts = pd.DataFrame({"account_id": ["U1", "U2", "U3"], "label": ["FRAUD", "REVIEW", "FRAUD"]})
            self.tx = pd.DataFrame()
            self.groups = []
            self.metrics = {"elapsed_s": 1.0, "total_transactions": 1, "total_accounts": 3, "fraud_accounts": 2, "review_accounts": 1}
            self.degraded = []

    import tracefx.evaluate
    # Monkeypatch pipeline_run locally to avoid setting up entire engine state
    original_run = tracefx.evaluate.pipeline_run
    try:
        tracefx.evaluate.pipeline_run = lambda df, cfg: MockPipelineResult()
        
        row = tracefx.evaluate._evaluate_seed(str(csv_path), str(truth_path), {})
        
        # Positives: U1, U2
        # Hard Negatives: U3 (never positive)
        # Pred FRAUD: U1, U3
        # Pred REVIEW: U2
        # Pred FRAUD+REVIEW: U1, U2, U3
        
        # Anyring tp_fraud_any: U1 (1)
        # Anyring precision_fraud: 1 / 2 = 0.5 (U1 / (U1, U3))
        assert row["precision_fraud_anyring"] == 0.5
        # Anyring recall_fraud: 1 / 2 = 0.5 (U1 / (U1, U2))
        assert row["recall_fraud_anyring"] == 0.5
        
        # tp_for_any: U1, U2 (2)
        # precision for_any: 2 / 3 = 0.6667 (U1, U2 / U1, U2, U3)
        assert round(row["precision_fraud_or_review_anyring"], 4) == 0.6667
        # recall for_any: 2 / 2 = 1.0 (U1, U2 / U1, U2)
        assert row["recall_fraud_or_review_anyring"] == 1.0
        
    finally:
        tracefx.evaluate.pipeline_run = original_run
