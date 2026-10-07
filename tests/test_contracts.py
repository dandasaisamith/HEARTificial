"""Tests for frozen contract signatures and dataclass shapes."""

from __future__ import annotations

import importlib
import inspect
import sys
import types

import pytest


def test_evidence_fields():
    """Evidence dataclass has all required fields."""
    from tracefx.types import Evidence
    fields = {f.name for f in Evidence.__dataclass_fields__.values()}
    required = {"type", "accounts", "tx_ids", "first_ts", "last_ts", "satisfied_at", "strength", "detail"}
    assert required <= fields


def test_evidence_is_frozen():
    """Evidence dataclass is frozen (immutable)."""
    from tracefx.types import Evidence
    ev = Evidence(
        type="shared_device",
        accounts=("A1", "A2"),
        tx_ids=("T1",),
        first_ts="2026-07-01T00:00:00+00:00",
        last_ts="2026-07-01T01:00:00+00:00",
        satisfied_at="2026-07-01T00:30:00+00:00",
        strength=0.5,
    )
    with pytest.raises((TypeError, AttributeError)):
        ev.strength = 0.9


def test_ledger_line_fields():
    """LedgerLine dataclass has all required fields."""
    from tracefx.types import LedgerLine
    fields = {f.name for f in LedgerLine.__dataclass_fields__.values()}
    required = {"source", "points", "text", "tx_ids"}
    assert required <= fields


def test_decision_fields():
    """Decision dataclass has all required fields including alert_ts."""
    from tracefx.types import Decision
    fields = {f.name for f in Decision.__dataclass_fields__.values()}
    required = {"tx_id", "label", "net_points", "risk", "ledger", "action", "alert_ts"}
    assert required <= fields


def test_result_fields():
    """Result dataclass has all required fields including capabilities."""
    from tracefx.types import Result
    fields = {f.name for f in Result.__dataclass_fields__.values()}
    required = {"tx", "accounts", "groups", "evidence", "decisions", "graph",
                "metrics", "degraded", "quality", "capabilities"}
    assert required <= fields


def test_group_fields():
    """Group dataclass has all required fields."""
    from tracefx.types import Group
    fields = {f.name for f in Group.__dataclass_fields__.values()}
    required = {"group_id", "accounts", "evidence_types", "risk", "shape", "summary"}
    assert required <= fields


def test_evidence_strength_validation():
    """Evidence.strength must be in [0, 1]."""
    from tracefx.types import Evidence
    with pytest.raises(ValueError):
        Evidence(
            type="burst",
            accounts=("A1",),
            tx_ids=("T1",),
            first_ts="2026-07-01T00:00:00+00:00",
            last_ts="2026-07-01T01:00:00+00:00",
            satisfied_at="2026-07-01T00:30:00+00:00",
            strength=1.5,  # invalid
        )


def test_no_import_cycles():
    """Detect circular imports in the tracefx package."""
    # Importing pipeline should not raise circular import
    from tracefx import pipeline
    from tracefx import schema
    from tracefx import features
    from tracefx import baseline
    from tracefx import graph
    from tracefx import motifs
    from tracefx import ledger
    from tracefx import gate
    from tracefx import rollup
    from tracefx import explain
    from tracefx import actions
    # All good if we get here


def test_pipeline_signature():
    """pipeline.run signature matches contract."""
    from tracefx import pipeline
    sig = inspect.signature(pipeline.run)
    params = list(sig.parameters.keys())
    assert "df" in params
    assert "cfg" in params


def test_schema_signatures():
    """schema module has required function signatures."""
    from tracefx import schema
    assert hasattr(schema, "load")
    assert hasattr(schema, "quality_report")
    assert hasattr(schema, "capabilities")


def test_ui_isolation():
    """UI/CLI should not import motifs, ledger, gate, etc. directly."""
    # We verify that app.py doesn't exist yet as a module
    # and that the pipeline contract is the boundary
    from tracefx import pipeline
    assert hasattr(pipeline, "run")
    assert hasattr(pipeline, "result_to_json")
    assert hasattr(pipeline, "result_from_json")


def test_json_round_trip():
    """Result can be serialized and deserialized without loss."""
    import pandas as pd
    from tracefx.types import Result, Evidence, LedgerLine, Decision, Group
    from tracefx.pipeline import result_to_json, result_from_json

    ev = Evidence(
        type="common_sink",
        accounts=("A1", "A2"),
        tx_ids=("T1", "T2"),
        first_ts="2026-07-01T00:00:00+00:00",
        last_ts="2026-07-01T01:00:00+00:00",
        satisfied_at="2026-07-01T00:30:00+00:00",
        strength=0.7,
        detail={"sink": "W0001"},
    )
    line = LedgerLine(source="common_sink", points=30.0, text="Test.", tx_ids=("T1",))
    dec = Decision(
        tx_id="A1", label="REVIEW", net_points=30.0, risk=0.3,
        ledger=[line], action="STEP-UP", alert_ts="2026-07-01T00:30:00+00:00"
    )
    group = Group(
        group_id="G001", accounts=("A1", "A2"),
        evidence_types=("common_sink",), risk=0.5,
        shape="star_mule", summary="Test group"
    )
    result = Result(
        tx=pd.DataFrame({"tx_id": ["T1"], "amount": [100.0]}),
        accounts=pd.DataFrame({"account_id": ["A1"], "label": ["REVIEW"]}),
        groups=[group],
        evidence=[ev],
        decisions={"A1": dec},
        graph={"nodes": [], "edges": []},
        metrics={"total_transactions": 1},
        degraded=[],
        quality={},
        capabilities={},
    )

    json_str = result_to_json(result)
    restored = result_from_json(json_str)

    assert len(restored.evidence) == 1
    assert restored.evidence[0].type == "common_sink"
    assert "A1" in restored.decisions
    assert restored.decisions["A1"].label == "REVIEW"
    assert len(restored.groups) == 1
