import pandas as pd
from tracefx import schema, config, pipeline
from pathlib import Path

def test_capabilities_full_vs_degraded(tmp_path):
    # Full dataset capabilities
    df_full = pd.DataFrame({
        "tx_id": ["1", "2"],
        "ts": ["2025-01-01T00:00:00Z", "2025-01-01T00:01:00Z"],
        "payer_id": ["P1", "P2"],
        "payee_id": ["M1", "M1"],
        "amount": [10.0, 20.0],
        "device_id": ["D1", "D2"],
        "ip": ["1.1.1.1", "2.2.2.2"]
    })
    
    full_path = tmp_path / "full.csv"
    df_full.to_csv(full_path, index=False)
    df_f = schema.load(full_path)
    cfg = config.default_config()
    res_f = pipeline.run(df_f, cfg)
    
    # Degraded dataset capabilities (missing device_id and ip)
    df_degraded = df_full.drop(columns=["device_id", "ip"])
    deg_path = tmp_path / "deg.csv"
    df_degraded.to_csv(deg_path, index=False)
    df_d = schema.load(deg_path)
    res_d = pipeline.run(df_d, cfg)
    
    assert bool(res_f.capabilities.get("device_evidence")) is True
    assert bool(res_f.capabilities.get("ip_evidence")) is True
    
    assert bool(res_d.capabilities.get("device_evidence")) is False
    assert bool(res_d.capabilities.get("ip_evidence")) is False

def test_external_hybrid_seed_exists():
    assert Path("data/external/hybrid_seed.csv").exists(), "Hybrid seed not generated."
    assert Path("data/external/truth_hybrid_seed.json").exists(), "Hybrid truth not generated."
