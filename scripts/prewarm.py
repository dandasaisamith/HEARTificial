"""Pre-warm the cache for TRACE-FX for demo purposes."""

import os
from pathlib import Path
from tracefx import schema, engine_api

def prewarm():
    paths = [Path("data"), Path("data/Traindata")]
    for base_dir in paths:
        if not base_dir.exists():
            continue
        for p in base_dir.rglob("*.csv"):
            if p.name.startswith("truth_") or "baseline" in p.name:
                continue
                
            try:
                print(f"Pre-warming {p.name}...")
                df = schema.load(str(p))
                
                # Check cache first
                cached, is_cached = engine_api.get_cached_run(str(p))
                if is_cached:
                    print(f"  {p.name} is already cached.")
                    continue
                    
                print(f"  Running pipeline for {p.name}...")
                res = engine_api.run_pipeline(df)
                engine_api.save_cached_run(str(p), res)
                print(f"  Successfully cached {p.name}")
            except Exception as e:
                print(f"  Skipped {p.name}: {e}")

if __name__ == "__main__":
    prewarm()
