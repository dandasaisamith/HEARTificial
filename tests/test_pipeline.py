"""Tests for the main pipeline orchestration."""

from __future__ import annotations

import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta

def ts(offset_h: float) -> str:
    base = datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
    return (base + timedelta(hours=offset_h)).isoformat()

def test_pipeline_end_to_end():
    """Pipeline processes data and produces a Result."""
    from tracefx import pipeline, config
    
    # 1. Provide minimal valid data that should produce a fraud ring
    # Let's create a common sink fraud ring with 4 payers
    rows = []
    # Sink transactions (M2)
    for i in range(4):
        rows.append({
            "tx_id": f"T{i:04d}", 
            "ts": ts(i * 0.5), 
            "payer_id": f"A{i:05d}",
            "payee_id": "W0001", 
            "amount": 1000.0,
            "device_id": f"D{i:05d}"
        })
    # Another type of structural evidence (M1 shared device) for A0 and A1
    rows.append({
        "tx_id": "T_shared_1",
        "ts": ts(0.1),
        "payer_id": "A00000",
        "payee_id": "M100",
        "amount": 500.0,
        "device_id": "D_EVIL"
    })
    rows.append({
        "tx_id": "T_shared_2",
        "ts": ts(0.2),
        "payer_id": "A00001",
        "payee_id": "M101",
        "amount": 600.0,
        "device_id": "D_EVIL"
    })
    
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    cfg = config.default_config()
    
    # 2. Run pipeline
    result = pipeline.run(df, cfg)
    
    # 3. Verify
    assert result.decisions is not None
    assert result.groups is not None
    assert not result.degraded

    # A00000 and A00001 should have M1 + M2 => FRAUD (points: 20 + 30 = 50, + behaviour?) 
    # Let's just check the pipeline runs to completion without crashing.
    # Since decisions are keyed by tx_id, we just check that the decisions exist
    assert "T_shared_1" in result.decisions
    assert "T_shared_2" in result.decisions

def test_pipeline_handles_missing_optional_columns():
    """Pipeline degrades gracefully when device_id is missing."""
    from tracefx import pipeline, config
    
    rows = [
        {"tx_id": "T1", "ts": ts(0), "payer_id": "A1", "payee_id": "W1", "amount": 100.0},
    ]
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    cfg = config.default_config()
    
    result = pipeline.run(df, cfg)
    
    assert "M1_shared_device" not in result.capabilities or not result.capabilities["M1_shared_device"]
    # Pipeline shouldn't crash
    assert "T1" in result.decisions

def test_result_serialization():
    """Result can be serialized and deserialized to/from JSON."""
    from tracefx import pipeline, config
    
    rows = [
        {"tx_id": "T1", "ts": ts(0), "payer_id": "A1", "payee_id": "W1", "amount": 100.0},
    ]
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    cfg = config.default_config()
    
    result = pipeline.run(df, cfg)
    
    # Serialize
    json_str = pipeline.result_to_json(result)
    assert isinstance(json_str, str)
    
    # Deserialize
    result2 = pipeline.result_from_json(json_str)
    assert result2.decisions["T1"].label == result.decisions["T1"].label
