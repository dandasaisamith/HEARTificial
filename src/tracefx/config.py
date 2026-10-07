"""Configuration loader and validator for TRACE-FX.

All thresholds and weights live in config.yaml.
This module validates and provides typed access to configuration.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

# Canonical key structure for validation
_REQUIRED_KEYS: dict[str, Any] = {
    "seed": int,
    "graph": {"deg_cap_device": int, "deg_cap_ip": int},
    "features": {"window_short_h": (int, float), "window_long_h": (int, float), "tenure_days_protect": (int, float)},
    "baseline": {"contamination": float, "behaviour_flag_pct": float},
    "motifs": {
        "common_sink": {"min_payers": int, "window_h": (int, float)},
        "pass_through": {"min_ratio": float, "window_min": (int, float)},
        "sequence": {"ngram": int, "min_shared_rare": int, "min_cohort": int, "idf_rare_quantile": float, "require_convergence": bool},
        "burst": {"z": float, "window_h": (int, float)},
        "sleeper": {"dormant_days": (int, float)},
    },
    "points": {
        "behaviour_max": (int, float),
        "shared_device": (int, float),
        "common_sink": (int, float),
        "pass_through": (int, float),
        "sequence_cohort": (int, float),
        "burst": (int, float),
        "sleeper": (int, float),
        "tenure_over_1y": (int, float),
        "repeat_payee_3plus": (int, float),
        "known_device_5plus": (int, float),
        "amount_within_p95": (int, float),
        "within_peer_range": (int, float),
    },
    "gate": {"fraud_net": (int, float), "fraud_min_structural_types": int, "review_net": (int, float)},
    "rollup": {"noisy_or": bool},
}

_OPTIONAL_KEYS = {"scorer", "limits"}


def _check_keys(cfg: dict, schema: dict, path: str = "") -> None:
    """Recursively validate config keys against schema."""
    for key, expected in schema.items():
        full = f"{path}.{key}" if path else key
        if key not in cfg:
            raise KeyError(f"Missing required config key: {full!r}")
        if isinstance(expected, dict):
            if not isinstance(cfg[key], dict):
                raise TypeError(f"Config key {full!r} must be a dict")
            _check_keys(cfg[key], expected, full)

    # Check for unknown keys (only at top level and known sub-dicts)
    known = set(schema.keys())
    for key in cfg:
        if key not in known:
            full = f"{path}.{key}" if path else key
            # Only warn about unknown top-level keys that aren't optional
            if not path and key not in _OPTIONAL_KEYS:
                raise KeyError(f"Unknown config key: {full!r}")


def load(path: str | Path | None = None) -> dict:
    """Load and validate config.yaml.

    Args:
        path: Path to config file. Defaults to config.yaml in project root.

    Returns:
        Validated configuration dict.

    Raises:
        KeyError: Missing or unknown configuration keys.
        FileNotFoundError: Config file not found.
    """
    if path is None:
        # Find config.yaml relative to the package
        here = Path(__file__).parent
        candidates = [
            here.parent.parent / "config.yaml",  # src/../.. (project root)
            here.parent / "config.yaml",
            Path("config.yaml"),
        ]
        for c in candidates:
            if c.exists():
                path = c
                break
        else:
            raise FileNotFoundError("config.yaml not found. Run from project root or specify path.")

    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    _check_keys(cfg, _REQUIRED_KEYS)
    return cfg


def get(cfg: dict, *keys: str, default: Any = None) -> Any:
    """Safe nested key access with default."""
    val = cfg
    for k in keys:
        if not isinstance(val, dict) or k not in val:
            return default
        val = val[k]
    return val


def default_config() -> dict:
    """Return a deep copy of the default configuration."""
    return copy.deepcopy({
        "seed": 42,
        "graph": {"deg_cap_device": 8, "deg_cap_ip": 8},
        "features": {"window_short_h": 1, "window_long_h": 24, "tenure_days_protect": 365},
        "baseline": {"contamination": 0.02, "behaviour_flag_pct": 0.97},
        "motifs": {
            "common_sink": {"min_payers": 4, "window_h": 24},
            "pass_through": {"min_ratio": 0.8, "window_min": 30},
            "sequence": {"ngram": 3, "min_shared_rare": 2, "min_cohort": 4, "idf_rare_quantile": 0.9, "require_convergence": True},
            "burst": {"z": 3.0, "window_h": 1},
            "sleeper": {"dormant_days": 90},
        },
        "points": {
            "behaviour_max": 20,
            "shared_device": 20,
            "common_sink": 30,
            "pass_through": 25,
            "sequence_cohort": 25,
            "burst": 10,
            "sleeper": 10,
            "tenure_over_1y": -15,
            "repeat_payee_3plus": -20,
            "known_device_5plus": -10,
            "amount_within_p95": -10,
            "within_peer_range": -5,
        },
        "gate": {"fraud_net": 60, "fraud_min_structural_types": 2, "review_net": 30},
        "rollup": {"noisy_or": True},
        "scorer": {"mode": "auto"},
        "limits": {"demo_rows": 5000, "eval_rows": 50000, "ui_max_rows": 200000},
    })
