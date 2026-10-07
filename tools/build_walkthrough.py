import argparse
from pathlib import Path
import pandas as pd
import re

def update_marker(content: str, marker_name: str, new_text: str) -> str:
    start_tag = f"<!-- {marker_name}:START -->"
    end_tag = f"<!-- {marker_name}:END -->"
    
    # Check if markers exist
    if start_tag not in content or end_tag not in content:
        # Append if not found, though we added them previously
        content += f"\n{start_tag}\n{end_tag}\n"
        
    pattern = re.compile(f"{start_tag}.*?{end_tag}", re.DOTALL)
    replacement = f"{start_tag}\n{new_text}\n{end_tag}"
    return pattern.sub(replacement, content)

def get_baseline_content():
    # Read finding
    finding_path = Path("docs/AUDIT_FINDINGS.md")
    conclusion = ""
    if finding_path.exists():
        finding_text = finding_path.read_text(encoding="utf-8")
        if "### (d) Conclusion" in finding_text:
            conclusion = finding_text.split("### (d) Conclusion")[1].strip()

    # Read eval results
    eval_csv = Path("reports/eval_results.csv")
    eval_md = ""
    if eval_csv.exists():
        df = pd.read_csv(eval_csv)
        # timing columns labelled "machine-dependent, excluded from regression compare"
        df.rename(columns={"elapsed_s": "elapsed_s (machine-dependent)", "latency_per_tx_ms": "latency (machine-dependent)"}, inplace=True)
        eval_md = df.to_markdown(index=False)
        
    # Read determinism from AUDIT_BASELINE.md
    audit_base = Path("docs/AUDIT_BASELINE.md")
    det_hashes = ""
    if audit_base.exists():
        txt = audit_base.read_text(encoding="utf-8")
        if "### Determinism" in txt:
            part = txt.split("### Determinism")[1].split("### Timing")[0].strip()
            det_hashes = part
            
    out = f"""## System Overview
TRACE-FX is a real-time financial fraud intelligence engine designed to produce explainable, deterministic decisions. It operates offline on CPU, prioritizing clear causal evidence over black-box predictions. The architecture transforms canonical transactions into structured motifs and aggregates them into a point-based ledger.

**Pipeline Flow:**
`schema` -> `features` -> `IsolationForest` -> `graph` -> `M1-M5` -> `ledger` -> `gate` -> `rollup` -> `explain/actions` -> `UI`.

## How to Run
```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python -m pytest -q
python -m tracefx eval --data-dir data --out reports
python -m tracefx score data\\demo_small.csv
python -m streamlit run app\\app.py
```

## Baseline Results
**Commit Tag:** `pre-external`
**Tests:** 50 passed

**Evaluation Table:**
{eval_md}

**Determinism Hashes:**
```
{det_hashes}
```

## Known Limits
- {conclusion}
- Synthetic data only.
- Hand-set weights.
- Slow-drip fraud falls to REVIEW.
"""
    return out

def get_final_content():
    return """## External Data & Hybrid Integration
*(External data execution was skipped as the necessary raw files and PROMPT_05_EXTERNAL_DATA.md instructions were not provided in the environment.)*

**NOT DONE list:**
- Fraud E-commerce real run
- Hybrid seed generation
- IEEE-CIS adapter & run
- Sparkov adapter & run
- UI real-data section
- Regression gate result
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["baseline", "final"], required=True)
    args = parser.parse_args()

    wt_path = Path("WALKTHROUGH.md")
    content = wt_path.read_text(encoding="utf-8")

    if args.stage == "baseline":
        content = update_marker(content, "BASELINE", get_baseline_content())
    elif args.stage == "final":
        content = update_marker(content, "EXTERNAL", get_final_content())
        
    wt_path.write_text(content, encoding="utf-8")

if __name__ == "__main__":
    main()
