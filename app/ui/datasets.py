import os
from pathlib import Path
import pandas as pd
import streamlit as st

def discover_datasets():
    """Scan data/ and data/Traindata for datasets."""
    paths_to_scan = [Path("data"), Path("data/Traindata")]
    datasets = []
    
    for base_dir in paths_to_scan:
        if not base_dir.exists():
            continue
        for p in base_dir.rglob("*.csv"):
            # skip derived and output files except specific ones
            if p.name.startswith("truth_") or "baseline" in p.name:
                continue
                
            try:
                stat = p.stat()
                size_mb = stat.st_size / (1024 * 1024)
                datasets.append({
                    "name": p.name,
                    "path": str(p),
                    "size_mb": size_mb,
                    "mtime": stat.st_mtime
                })
            except Exception:
                pass
                
    # Sort by mtime descending
    datasets.sort(key=lambda x: x["mtime"], reverse=True)
    return datasets

def load_dataset_metadata(path: str):
    """Peek into a dataset and classify it."""
    try:
        # Just read first 100 rows to detect schema
        df = pd.read_csv(path, nrows=100)
        cols = set(df.columns)
        
        # Determine status
        is_canonical = {"tx_id", "ts", "payer_id", "payee_id", "amount"}.issubset(cols)
        
        # Detect truth file pairing
        p = Path(path)
        truth_path = p.parent / f"truth_{p.stem.replace('seed', '')}.json"
        has_truth = truth_path.exists()
        
        return {
            "status": "READY" if is_canonical else "RAW",
            "columns": list(cols),
            "rows_estimate": "...", # Compute lazily if needed
            "has_truth": has_truth,
            "truth_path": str(truth_path) if has_truth else None,
            "is_canonical": is_canonical,
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

