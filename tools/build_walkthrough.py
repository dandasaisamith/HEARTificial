import argparse
from pathlib import Path
import pandas as pd
import re
import subprocess

def update_marker(content: str, marker_name: str, new_text: str) -> str:
    start_tag = f"<!-- {marker_name}:START -->"
    end_tag = f"<!-- {marker_name}:END -->"
    
    if start_tag not in content or end_tag not in content:
        content += f"\n{start_tag}\n{end_tag}\n"
        
    pattern = re.compile(f"{start_tag}.*?{end_tag}", re.DOTALL)
    replacement = f"{start_tag}\n{new_text}\n{end_tag}"
    match = pattern.search(content)
    if match:
        content = content[:match.start()] + replacement + content[match.end():]
    return content

def get_baseline_content():
    finding_path = Path("docs/AUDIT_FINDINGS.md")
    conclusion = ""
    if finding_path.exists():
        finding_text = finding_path.read_text(encoding="utf-8")
        if "### (d) Conclusion" in finding_text:
            conclusion = finding_text.split("### (d) Conclusion")[1].strip()

    eval_csv = Path("reports/eval_results.csv")
    eval_md = ""
    if eval_csv.exists():
        df = pd.read_csv(eval_csv)
        df.rename(columns={"elapsed_s": "elapsed_s (machine-dependent)", "latency_per_tx_ms": "latency (machine-dependent)"}, inplace=True)
        cols = df.columns.tolist()
        eval_md = "| " + " | ".join(cols) + " |\n"
        eval_md += "| " + " | ".join(["---"] * len(cols)) + " |\n"
        for _, row in df.iterrows():
            eval_md += "| " + " | ".join(str(row[c]) for c in cols) + " |\n"
        
    audit_base = Path("docs/AUDIT_BASELINE.md")
    det_hashes = ""
    if audit_base.exists():
        txt = audit_base.read_text(encoding="utf-8")
        if "### Determinism" in txt:
            part = txt.split("### Determinism")[1].split("### Timing")[0].strip()
            det_hashes = part

    # Read pytest count
    pytest_count = "Unknown"
    if audit_base.exists() and "passed" in txt:
        import re
        m = re.search(r"(\d+)\s+passed", txt)
        if m:
            pytest_count = m.group(1) + " passed"

    # Get git tags
    try:
        tags = subprocess.check_output(["git", "tag", "--list"], text=True).strip().split("\n")
        commit_tag = ", ".join(t for t in tags if t) if tags and tags[0] else "none"
    except Exception:
        commit_tag = "unknown"

    out = f"""## System Overview
TRACE-FX is a real-time-oriented fraud intelligence engine with causal temporal replay and batch scoring. It operates offline on CPU, prioritizing clear causal evidence over black-box predictions. The architecture transforms canonical transactions into structured motifs and aggregates them into a point-based ledger.

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
**Commit Tag:** {commit_tag}
**Tests:** {pytest_count}

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

def read_file_or_fallback(path: str) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8") if p.exists() else "not produced"

def get_final_content():
    ext_eval = "not produced"
    eval_p = Path("reports/external_eval.csv")
    if eval_p.exists():
        df = pd.read_csv(eval_p)
        cols = df.columns.tolist()
        ext_eval = "| " + " | ".join(cols) + " |\n"
        ext_eval += "| " + " | ".join(["---"] * len(cols)) + " |\n"
        for _, row in df.iterrows():
            ext_eval += "| " + " | ".join(str(row[c]) for c in cols) + " |\n"

    ext_summary = read_file_or_fallback("reports/EXTERNAL_SUMMARY.md")
    tuning_log = read_file_or_fallback("docs/TUNING_LOG.md")
    reg_gate = read_file_or_fallback("reports/regression_gate.txt")
    
    scope_p = Path("SCOPE.md")
    not_done_items = []
    if scope_p.exists():
        for line in scope_p.read_text(encoding="utf-8").split("\n"):
            if "NOT DONE" in line:
                not_done_items.append(line.replace("NOT DONE", "").strip(" -|[]"))
    not_done_text = "\\n- ".join(not_done_items) if not_done_items else "none"

    return f"""## External Data & Hybrid Integration
**External Evaluation:**
{ext_eval}

**External Summary:**
{ext_summary}

**Tuning Log:**
{tuning_log}

**Regression Gate:**
{reg_gate}

**NOT DONE list:**
- {not_done_text}
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
