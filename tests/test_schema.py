"""Tests for schema loading, validation, and capability detection."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pytest


def make_minimal_df(**kwargs) -> pd.DataFrame:
    """Create a minimal valid transaction DataFrame."""
    data = {
        "tx_id": ["T0000001", "T0000002"],
        "ts": ["2026-07-01T00:00:00Z", "2026-07-01T01:00:00Z"],
        "payer_id": ["A10001", "A10002"],
        "payee_id": ["A20001", "A20002"],
        "amount": ["1000.00", "2000.00"],
    }
    data.update(kwargs)
    return pd.DataFrame(data)


def save_csv(df: pd.DataFrame, path: Path) -> Path:
    df.to_csv(path, index=False)
    return path


def test_load_minimal(tmp_path):
    """Schema loads a minimal 5-column CSV."""
    from tracefx import schema
    path = save_csv(make_minimal_df(), tmp_path / "test.csv")
    df = schema.load(path)
    assert set(["tx_id", "ts", "payer_id", "payee_id", "amount"]) <= set(df.columns)
    assert len(df) == 2


def test_ts_normalized_to_utc(tmp_path):
    """Timestamps are parsed and normalized to UTC."""
    from tracefx import schema
    path = save_csv(make_minimal_df(), tmp_path / "test.csv")
    df = schema.load(path)
    assert df["ts"].dt.tz is not None
    assert str(df["ts"].dt.tz) == "UTC"


def test_deduplication(tmp_path):
    """Duplicate tx_ids are removed (keep first)."""
    from tracefx import schema
    df_data = make_minimal_df()
    df_data = pd.concat([df_data, df_data.iloc[[0]]])  # duplicate first row
    path = save_csv(df_data, tmp_path / "test.csv")
    df = schema.load(path)
    assert df["tx_id"].nunique() == len(df)


def test_missing_required_column(tmp_path):
    """Loading a CSV missing a required column raises ValueError."""
    from tracefx import schema
    df = make_minimal_df()
    df = df.drop(columns=["payer_id"])
    path = save_csv(df, tmp_path / "bad.csv")
    with pytest.raises(ValueError, match="Missing required columns"):
        schema.load(path)


def test_malformed_timestamps(tmp_path):
    """Rows with malformed timestamps are dropped."""
    from tracefx import schema
    df = make_minimal_df(ts=["NOTADATE", "2026-07-01T01:00:00Z"])
    path = save_csv(df, tmp_path / "test.csv")
    df_out = schema.load(path)
    assert len(df_out) == 1  # one row dropped


def test_column_mapping(tmp_path):
    """Column mapping renames input columns to canonical names."""
    from tracefx import schema
    df = pd.DataFrame({
        "transaction_id": ["T1"],
        "datetime": ["2026-07-01T00:00:00Z"],
        "sender": ["A1"],
        "receiver": ["A2"],
        "value": [500.0],
    })
    path = save_csv(df, tmp_path / "test.csv")
    df_out = schema.load(path)
    assert "tx_id" in df_out.columns
    assert "ts" in df_out.columns
    assert "payer_id" in df_out.columns
    assert "payee_id" in df_out.columns
    assert "amount" in df_out.columns


def test_file_not_found():
    """Loading a non-existent file raises FileNotFoundError."""
    from tracefx import schema
    with pytest.raises(FileNotFoundError):
        schema.load("/nonexistent/path/file.csv")


def test_capabilities_with_device(tmp_path):
    """Capabilities returns device_evidence=True when device_id present."""
    from tracefx import schema
    df = make_minimal_df()
    df["device_id"] = ["D001", "D002"]
    path = save_csv(df, tmp_path / "test.csv")
    df_out = schema.load(path)
    caps = schema.capabilities(df_out)
    assert bool(caps["device_evidence"]) is True
    assert bool(caps["M1_shared_device"]) is True


def test_capabilities_minimal_only(tmp_path):
    """With only required columns, M1 and M4 are unavailable."""
    from tracefx import schema
    path = save_csv(make_minimal_df(), tmp_path / "test.csv")
    df = schema.load(path)
    caps = schema.capabilities(df)
    assert caps["M1_shared_device"] is False
    assert caps["M4_sequence_cohort"] is False
    assert caps["M2_common_sink"] is True
    assert caps["M3_pass_through"] is True


def test_quality_report(tmp_path):
    """quality_report returns expected structure."""
    from tracefx import schema
    path = save_csv(make_minimal_df(), tmp_path / "test.csv")
    df = schema.load(path)
    report = schema.quality_report(df)
    assert "total_rows" in report
    assert "amount_stats" in report
    assert "capabilities" in report
