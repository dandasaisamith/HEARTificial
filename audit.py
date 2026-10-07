import os
import subprocess
import time
import hashlib
import json

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return res.stdout, res.stderr, res.returncode
    except Exception as e:
        return "", str(e), -1

def main():
    report = []
    
    # 1. git status and log
    out, err, _ = run_cmd("git status")
    report.append("### git status\n" + out + "\n" + err)
    out, err, _ = run_cmd("git log --oneline -n 15")
    report.append("### git log\n" + out + "\n" + err)
    
    # 2. Pytest results
    out, err, _ = run_cmd("python -m pytest -q")
    report.append("### pytest\n" + out + "\n" + err)
    
    # 3. Data generation
    if not all(os.path.exists(f"data/{f}") for f in ["seedA.csv", "seedB.csv", "seedC.csv", "demo_small.csv"]):
        out, err, _ = run_cmd("python -m tracefx data")
        report.append("### tracefx data\n" + out + "\n" + err)
    
    # 4. Evaluation
    try:
        with open("reports/eval_results.csv", "r") as f:
            report.append("### eval_results.csv\n" + f.read())
    except Exception as e:
        report.append("### eval_results.csv\n" + str(e))
        
    # 5. UI Smoke
    ui_cmd = "python -c \"from streamlit.testing.v1 import AppTest; at=AppTest.from_file('app/app.py', default_timeout=120).run(); print('EXCEPTIONS:', [str(e.value) for e in at.exception])\""
    out, err, _ = run_cmd(ui_cmd)
    report.append("### UI Smoke\n" + out + "\n" + err)
    
    # 6. Determinism & Timing
    import pandas as pd
    from tracefx.pipeline import run, result_to_json
    from tracefx.config import load
    from tracefx.schema import load as load_data
    import json
    
    df = load_data("data/demo_small.csv")
    cfg = load("config.yaml")
    
    t0 = time.time()
    res1 = run(df, cfg)
    t1 = time.time()
    res2 = run(df, cfg)
    t2 = time.time()
    
    t_demo = t1 - t0
    
    df_a = load_data("data/seedA.csv")
    t0 = time.time()
    run(df_a, cfg)
    t_seeda = time.time() - t0
    
    d1 = json.loads(result_to_json(res1))
    d2 = json.loads(result_to_json(res2))
    
    # Remove timing metrics that break determinism
    d1["metrics"].pop("elapsed_s", None)
    d2["metrics"].pop("elapsed_s", None)
    
    j1 = json.dumps(d1, sort_keys=True)
    j2 = json.dumps(d2, sort_keys=True)
    
    h1 = hashlib.sha256(j1.encode()).hexdigest()
    h2 = hashlib.sha256(j2.encode()).hexdigest()
    
    report.append(f"### Determinism\nHash1: {h1}\nHash2: {h2}\nEqual: {h1 == h2}")
    report.append(f"### Timing\nDemo small: {t_demo:.2f}s ({t_demo/len(df):.5f}s/tx)\nSeed A: {t_seeda:.2f}s ({t_seeda/len(df_a):.5f}s/tx)")
    
    # Check C1
    c1_pass = True
    for t_id, dec in res1.decisions.items():
        if len(dec.ledger) < 1:
            c1_pass = False
            break
    report.append(f"### C1: tx-level decisions with ledger >= 1: {c1_pass}")
    
    with open("docs/AUDIT_BASELINE.md", "w") as f:
        f.write("\n\n".join(report))
        
if __name__ == '__main__':
    main()
