"""Tests for config loading and validation."""

from __future__ import annotations

import pytest
import yaml
from pathlib import Path


def test_load_default_config():
    """Config loads from config.yaml without error."""
    from tracefx import config
    cfg = config.load()
    assert "gate" in cfg
    assert "points" in cfg
    assert cfg["gate"]["fraud_net"] == 60
    assert cfg["gate"]["fraud_min_structural_types"] == 2
    assert cfg["gate"]["review_net"] == 30


def test_default_config_complete():
    """default_config() returns all required keys."""
    from tracefx import config
    cfg = config.default_config()
    assert cfg["points"]["shared_device"] == 20
    assert cfg["points"]["common_sink"] == 30
    assert cfg["points"]["tenure_over_1y"] == -15


def test_config_rejects_unknown_keys(tmp_path):
    """Config validator rejects unknown top-level keys."""
    from tracefx import config
    cfg_data = config.default_config()
    cfg_data["unknown_evil_key"] = "bad"
    cfg_path = tmp_path / "bad_config.yaml"
    cfg_path.write_text(yaml.dump(cfg_data))
    with pytest.raises(KeyError, match="Unknown config key"):
        config.load(cfg_path)


def test_config_rejects_missing_keys(tmp_path):
    """Config validator rejects configs missing required keys."""
    from tracefx import config
    cfg_data = config.default_config()
    del cfg_data["gate"]
    cfg_path = tmp_path / "missing_config.yaml"
    cfg_path.write_text(yaml.dump(cfg_data))
    with pytest.raises(KeyError, match="Missing required config key"):
        config.load(cfg_path)


def test_points_from_config():
    """All point values come from config, not hard-coded."""
    from tracefx import config
    cfg = config.default_config()
    pts = cfg["points"]
    # All expected point keys present
    for key in ["behaviour_max", "shared_device", "common_sink", "pass_through",
                "sequence_cohort", "burst", "sleeper", "tenure_over_1y",
                "repeat_payee_3plus", "known_device_5plus", "amount_within_p95",
                "within_peer_range"]:
        assert key in pts, f"Missing points key: {key}"


def test_graph_hub_caps_in_config():
    """Graph hub caps are in config."""
    from tracefx import config
    cfg = config.default_config()
    assert cfg["graph"]["deg_cap_device"] == 8
    assert cfg["graph"]["deg_cap_ip"] == 8

def test_config_overlay(tmp_path):
    from tracefx import config
    cfg_path = tmp_path / "base.yaml"
    cfg_data = config.default_config()
    cfg_path.write_text(yaml.dump(cfg_data))
    
    ov_path = tmp_path / "ov.yaml"
    ov_path.write_text(yaml.dump({"gate": {"fraud_net": 70}, "features": {"use_since_open": True}}))
    
    cfg = config.load(cfg_path, ov_path)
    assert cfg["gate"]["fraud_net"] == 70
    assert cfg["gate"]["fraud_min_structural_types"] == 2
    assert cfg["features"]["use_since_open"] is True

def test_config_overlay_rejects_unknown(tmp_path):
    from tracefx import config
    cfg_path = tmp_path / "base.yaml"
    cfg_data = config.default_config()
    cfg_path.write_text(yaml.dump(cfg_data))
    
    ov_path = tmp_path / "ov.yaml"
    ov_path.write_text(yaml.dump({"unknown_evil_key": "bad"}))
    
    import pytest
    with pytest.raises(KeyError, match="Unknown config key"):
        config.load(cfg_path, ov_path)
