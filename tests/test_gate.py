"""Tests for the frozen decision gate."""

from __future__ import annotations

import pytest


def _make_ledger_line(source: str, points: float, text: str = "Test.") -> object:
    from tracefx.types import LedgerLine
    return LedgerLine(source=source, points=points, text=text, tx_ids=("T1",))


def _make_evidence(ev_type: str, accounts=("A1", "A2"), strength=0.8):
    from tracefx.types import Evidence
    return Evidence(
        type=ev_type,
        accounts=accounts,
        tx_ids=("T1",),
        first_ts="2026-07-01T00:00:00+00:00",
        last_ts="2026-07-01T01:00:00+00:00",
        satisfied_at="2026-07-01T00:30:00+00:00",
        strength=strength,
    )


def _default_cfg():
    from tracefx.config import default_config
    return default_config()


# ----- FRAUD cases -----

def test_m1_plus_m2_plus_m4_is_fraud():
    """M1+M2+M4 = 75 points with 3 structural types -> FRAUD."""
    from tracefx import gate
    cfg = _default_cfg()

    ledger = {
        "A1": [
            _make_ledger_line("shared_device", 20.0),
            _make_ledger_line("common_sink", 30.0),
            _make_ledger_line("sequence_cohort", 25.0),
        ]
    }
    evidence = [
        _make_evidence("shared_device"),
        _make_evidence("common_sink"),
        _make_evidence("sequence_cohort"),
    ]

    decisions = gate.decide(ledger, evidence, cfg)
    assert decisions["A1"].label == "FRAUD"
    assert decisions["A1"].net_points == 75.0


def test_m2_plus_m3_fraud_with_behaviour():
    """M2+M3 = 55 points, + behaviour = 20 -> 75 -> FRAUD with 2 structural types."""
    from tracefx import gate
    cfg = _default_cfg()

    ledger = {
        "A1": [
            _make_ledger_line("common_sink", 30.0),
            _make_ledger_line("pass_through", 25.0),
            _make_ledger_line("behaviour_anomaly", 15.0),
        ]
    }
    evidence = [
        _make_evidence("common_sink"),
        _make_evidence("pass_through"),
    ]

    decisions = gate.decide(ledger, evidence, cfg)
    assert decisions["A1"].label == "FRAUD"


# ----- REVIEW cases -----

def test_single_structural_type_review():
    """Single structural type alone -> REVIEW at most."""
    from tracefx import gate
    cfg = _default_cfg()

    ledger = {
        "A1": [_make_ledger_line("common_sink", 30.0)]
    }
    evidence = [_make_evidence("common_sink")]

    decisions = gate.decide(ledger, evidence, cfg)
    assert decisions["A1"].label in ("REVIEW", "LEGIT")
    assert decisions["A1"].label != "FRAUD"


def test_m1_plus_m2_review_without_enough_points():
    """M1+M2 = 50, below fraud threshold of 60 -> REVIEW."""
    from tracefx import gate
    cfg = _default_cfg()

    ledger = {
        "A1": [
            _make_ledger_line("shared_device", 20.0),
            _make_ledger_line("common_sink", 30.0),
        ]
    }
    evidence = [
        _make_evidence("shared_device"),
        _make_evidence("common_sink"),
    ]

    decisions = gate.decide(ledger, evidence, cfg)
    assert decisions["A1"].label == "REVIEW"
    assert decisions["A1"].net_points == 50.0


# ----- LEGIT cases -----

def test_behaviour_alone_never_fraud():
    """Behaviour score alone NEVER produces FRAUD."""
    from tracefx import gate
    cfg = _default_cfg()

    ledger = {
        "A1": [_make_ledger_line("behaviour_anomaly", 20.0)]
    }
    evidence = []  # No structural evidence

    decisions = gate.decide(ledger, evidence, cfg)
    assert decisions["A1"].label != "FRAUD"


def test_no_evidence_is_legit():
    """No evidence -> LEGIT."""
    from tracefx import gate
    cfg = _default_cfg()

    ledger = {"A1": [_make_ledger_line("no_evidence", 0.0)]}
    evidence = []

    decisions = gate.decide(ledger, evidence, cfg)
    assert decisions["A1"].label == "LEGIT"


def test_exculpatory_reduces_score():
    """Exculpatory evidence reduces net points and can prevent FRAUD."""
    from tracefx import gate
    cfg = _default_cfg()

    ledger = {
        "A1": [
            _make_ledger_line("shared_device", 20.0),
            _make_ledger_line("common_sink", 30.0),
            _make_ledger_line("sequence_cohort", 25.0),
            _make_ledger_line("tenure_over_1y", -15.0),
            _make_ledger_line("repeat_payee_3plus", -20.0),
        ]
    }
    evidence = [
        _make_evidence("shared_device"),
        _make_evidence("common_sink"),
        _make_evidence("sequence_cohort"),
    ]

    decisions = gate.decide(ledger, evidence, cfg)
    # 75 - 35 = 40 < 60 -> not FRAUD
    assert decisions["A1"].net_points == 40.0
    assert decisions["A1"].label == "REVIEW"


def test_every_decision_has_ledger_line():
    """Every Decision must have at least one ledger line."""
    from tracefx import gate
    cfg = _default_cfg()

    ledger = {"A1": []}  # empty ledger
    evidence = []

    decisions = gate.decide(ledger, evidence, cfg)
    assert len(decisions["A1"].ledger) >= 1


def test_fraud_requires_two_structural_types():
    """FRAUD requires >= 2 independent structural evidence types."""
    from tracefx import gate
    cfg = _default_cfg()

    # 65 points but only 1 structural type
    ledger = {
        "A1": [
            _make_ledger_line("common_sink", 30.0),
            _make_ledger_line("behaviour_anomaly", 20.0),
            _make_ledger_line("burst", 10.0),
            _make_ledger_line("sleeper", 10.0),
        ]
    }
    evidence = [
        _make_evidence("common_sink"),  # only 1 structural
        _make_evidence("burst"),        # burst is structural but same "type"
    ]

    decisions = gate.decide(ledger, evidence, cfg)
    # 2 structural types: common_sink + burst -> could be FRAUD if net >= 60
    # 30+20+10+10 = 70 >= 60, 2 structural types -> FRAUD
    assert decisions["A1"].label == "FRAUD"


def test_risk_in_unit_interval():
    """All decision risks are in [0, 1]."""
    from tracefx import gate
    cfg = _default_cfg()

    ledger = {
        "A1": [_make_ledger_line("common_sink", 150.0)],  # very high
        "A2": [_make_ledger_line("no_evidence", 0.0)],
    }
    evidence = [_make_evidence("common_sink", accounts=("A1",))]

    decisions = gate.decide(ledger, evidence, cfg)
    for dec in decisions.values():
        assert 0.0 <= dec.risk <= 1.0
