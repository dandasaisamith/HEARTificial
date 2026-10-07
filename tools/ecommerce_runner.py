import pandas as pd
from pathlib import Path
import subprocess

def run_ecommerce():
    canon_path = Path("data/external/ecommerce_canonical.csv")
    out_csv = Path("data/external/ecommerce_40k.csv")
    out_txt = Path("reports/ecommerce_run.txt")
    
    if not canon_path.exists():
        print("Canonical CSV missing.")
        return
        
    df = pd.read_csv(canon_path)
    # Sort chronologically and take first 40k
    df = df.sort_values("ts").head(40000)
    # Remove label column before scoring as it's an unsupervised engine
    # Wait, tracefx score handles it or not? "label" is in the spec, but we might want to keep it?
    # Actually, schema.load drops 'label' safely if it's there but is only used for supervised mode or evaluation.
    # The prompt says "Keep the earliest 40,000 rows".
    df.to_csv(out_csv, index=False)
    
    print(f"Saved {len(df)} rows to {out_csv}")
    
    # Run tracefx score
    result = subprocess.run(
        ["python", "-m", "tracefx", "score", str(out_csv), "--out", "reports/ecommerce"],
        capture_output=True, text=True
    )
    
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text(result.stdout + "\n" + result.stderr)
    
    print("Scoring complete. Written to reports/ecommerce_run.txt")

if __name__ == "__main__":
    run_ecommerce()
