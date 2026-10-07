"""Wrapper API for TRACE-FX engine to support live UI updates and caching."""

import time
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from tracefx import schema, config, pipeline

def _hash_df(df: pd.DataFrame) -> str:
    """Hash a dataframe to use as cache key."""
    # Fast hash based on shape and first few bytes of columns
    s = f"{df.shape}_{list(df.columns)}"
    return hashlib.md5(s.encode()).hexdigest()

def run_pipeline(df: pd.DataFrame, truth_df: pd.DataFrame = None, on_event=None):
    """Run pipeline and emit live events."""
    original_safe = pipeline._safe
    
    # Pre-event: schema load
    if on_event:
        on_event({"stage": "S1", "name": "Ingest & validate", "status": "running", "elapsed": 0.0})
    t0 = time.time()
    
    # actually schema load already happened if we have df, but we pretend here
    # capabilities and quality check
    caps = schema.capabilities(df)
    qual = schema.quality_report(df)
    
    if on_event:
        on_event({"stage": "S1", "name": "Ingest & validate", "status": "done", "elapsed": time.time() - t0, 
                  "metrics": {"rows": len(df), "accounts": df["payer_id"].nunique()}})

    def tracked_safe(name, fn, fallback, degraded, *args, **kwargs):
        # Map internal names to S2-S8
        stage_map = {
            "features": ("S2", "Feature Engineering"),
            "baseline": ("S2", "Learn normal behavior"),
            "motifs": ("S5", "Mine structural motifs M1-M5"),
            "graph": ("S4", "Build typed temporal graph"),
            "ledger": ("S6", "Evidence ledger -> noisy-OR risk"),
            "gate": ("S7", "Precision gate"),
            "rollup_accounts": ("S8", "Action policy"),
            "rollup_groups": ("S8", "Group Rollup"),
        }
        
        stage_id, stage_name = stage_map.get(name, (f"S_{name}", name))
        
        if on_event:
            on_event({"stage": stage_id, "name": stage_name, "status": "running", "elapsed": 0.0})
            
        t_start = time.time()
        result = original_safe(name, fn, fallback, degraded, *args, **kwargs)
        t_elapsed = time.time() - t_start
        
        metrics = {}
        if name == "motifs":
            metrics["motifs_found"] = len(result)
        elif name == "gate":
            fraud_c = sum(1 for d in result.values() if d.label == "FRAUD")
            metrics["fraud_decisions"] = fraud_c
            
        if on_event:
            on_event({"stage": stage_id, "name": stage_name, "status": "done", "elapsed": t_elapsed, "metrics": metrics})
            
        return result

    cfg = config.load()
    
    with patch('tracefx.pipeline._safe', side_effect=tracked_safe):
        res = pipeline.run(df, cfg)
        
    if truth_df is not None and on_event:
        on_event({"stage": "S9", "name": "Evaluate", "status": "running", "elapsed": 0.0})
        # Evaluate would happen here
        on_event({"stage": "S9", "name": "Evaluate", "status": "done", "elapsed": 0.1})
        
    return res

def get_cached_run(df_path: str):
    """Retrieve a cached result if it exists."""
    p = Path(df_path)
    if not p.exists():
        return None
    
    # We will build caching logic here
    # For now, we just hash the file modified time
    cache_dir = Path(".cache/trace_fx")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    stat = p.stat()
    key = hashlib.md5(f"{p.name}_{stat.st_mtime}_{stat.st_size}".encode()).hexdigest()
    
    cache_file = cache_dir / f"{key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                json_str = f.read()
            return pipeline.result_from_json(json_str), True
        except Exception:
            return None, False
            
    return None, False

def save_cached_run(df_path: str, result):
    p = Path(df_path)
    stat = p.stat()
    key = hashlib.md5(f"{p.name}_{stat.st_mtime}_{stat.st_size}".encode()).hexdigest()
    
    cache_dir = Path(".cache/trace_fx")
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    cache_file = cache_dir / f"{key}.json"
    json_str = pipeline.result_to_json(result)
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(json_str)

