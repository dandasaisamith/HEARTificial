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
        from tracefx import schema
        
        # We can cache this, but for now we'll do a quick read
        # For large files, we might just want to read the whole thing if it's <100MB
        p = Path(path)
        stat = p.stat()
        size_mb = stat.st_size / (1024 * 1024)
        
        if size_mb < 50: # if < 50MB, load fully to get accurate stats
            df = pd.read_csv(path, dtype=str)
            cols = set(df.columns)
            is_canonical = {"tx_id", "ts", "payer_id", "payee_id", "amount"}.issubset(cols)
            
            rows = len(df)
            if "payer_id" in cols:
                accounts = df["payer_id"].nunique()
            else:
                accounts = "Unknown"
                
            if "ts" in cols:
                try:
                    df["ts_dt"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
                    time_range = f"{df['ts_dt'].min().strftime('%Y-%m-%d')} to {df['ts_dt'].max().strftime('%Y-%m-%d')}"
                except:
                    time_range = "Unknown"
            else:
                time_range = "Unknown"
                
            caps = schema.capabilities(df)
        else:
            # Quick peek for massive files
            df = pd.read_csv(path, nrows=100)
            cols = set(df.columns)
            is_canonical = {"tx_id", "ts", "payer_id", "payee_id", "amount"}.issubset(cols)
            rows = "Large Dataset (>50MB)"
            accounts = "Unknown"
            time_range = "Unknown"
            caps = schema.capabilities(df)
            
        truth_path = p.parent / f"truth_{p.stem.replace('seed', '')}.json"
        has_truth = truth_path.exists()
        
        return {
            "status": "READY" if is_canonical else "RAW",
            "columns": list(cols),
            "rows": rows,
            "accounts": accounts,
            "time_range": time_range,
            "capabilities": caps,
            "has_truth": has_truth,
            "truth_path": str(truth_path) if has_truth else None,
            "is_canonical": is_canonical,
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

