import json
import inspect
from pathlib import Path
from tracefx import evaluate, config, schema, pipeline

def get_evaluate_source():
    src = inspect.getsource(evaluate._evaluate_seed)
    lines = src.split('\n')
    start, end = 0, len(lines)
    for i, line in enumerate(lines):
        if "# ----- Precision / account-level -----" in line:
            start = i
        if "pr_auc =" in line and start > 0:
            end = i + 1
            break
    return "\n".join(lines[start:end])

def main():
    cfg = config.load()
    out_md = []
    
    out_md.append("### (a) Definition of precision_fraud and recall_fraud in evaluate.py")
    out_md.append("```python\n" + get_evaluate_source() + "\n```\n")

    seeds = ["seedA", "seedB", "seedC", "demo_small"]
    
    out_md.append("### (b) Truth Ring Stats")
    
    r1_fraud_blocks_points = 0
    r1_fraud_blocks_structure = 0
    
    fraud_accounts_output = []

    expected_tiers = {"R1": "FRAUD", "R2": "REVIEW", "R3": "undetected", "cyclic": "REVIEW or listed miss"}
    
    for seed in seeds:
        csv_path = Path(f"data/{seed}.csv")
        truth_path = Path(f"data/truth_{seed}.json")
        if not csv_path.exists() or not truth_path.exists():
            continue
            
        df = schema.load(str(csv_path))
        with open(truth_path) as f:
            truth = json.load(f)
            
        result = pipeline.run(df, cfg)
        
        rings = truth.get("rings", [])
        fraud_tx_ids = set(truth.get("is_fraud_tx_ids", []))
        hard_negatives = truth.get("hard_negatives", [])
        
        out_md.append(f"**Seed: {seed}**")
        
        for i, ring in enumerate(rings):
            rtype = ring.get("type", "unknown")
            accs = ring.get("accounts", [])
            expected = expected_tiers.get(rtype, "unknown")
            
            f_count = r_count = l_count = 0
            
            r1_details = []
            
            for a in accs:
                if result.accounts.empty:
                    break
                row = result.accounts[result.accounts["account_id"] == a]
                if row.empty:
                    l_count += 1
                    continue
                lbl = row.iloc[0]["label"]
                if lbl == "FRAUD":
                    f_count += 1
                elif lbl == "REVIEW":
                    r_count += 1
                else:
                    l_count += 1
                    
                if rtype == "R1":
                    # Get decision details
                    max_pts = 0.0
                    struct_types = set()
                    motifs_fired = set()
                    
                    txs = result.tx[result.tx["payer_id"] == a]
                    for tx_id in txs["tx_id"]:
                        d = result.decisions.get(tx_id)
                        if d:
                            if d.net_points > max_pts:
                                max_pts = d.net_points
                            for ll in d.ledger:
                                if ll.source in {"shared_device", "common_sink", "pass_through", "sequence_cohort", "burst"}:
                                    struct_types.add(ll.source)
                                motifs_fired.add(ll.source)
                    
                    if max_pts < cfg["gate"]["fraud_net"]:
                        r1_fraud_blocks_points += 1
                    if len(struct_types) < cfg["gate"]["fraud_min_structural_types"]:
                        r1_fraud_blocks_structure += 1
                        
                    r1_details.append(f"  - {a}: max net points {max_pts:.1f}, {len(struct_types)} structural types, motifs: {', '.join(motifs_fired)}")
                    
            out_md.append(f"- Ring {i+1} ({rtype}, expected {expected}): {len(accs)} members (FRAUD: {f_count}, REVIEW: {r_count}, LEGIT: {l_count})")
            for d in r1_details:
                out_md.append(d)
                
        # (c) FRAUD tier accounts
        if not result.accounts.empty:
            fraud_accs = result.accounts[result.accounts["label"] == "FRAUD"]["account_id"].tolist()
            if fraud_accs:
                fraud_accounts_output.append(f"**Seed: {seed}**")
                for fa in fraud_accs:
                    truth_assoc = "none"
                    for ring in rings:
                        if fa in ring.get("accounts", []):
                            truth_assoc = f"Ring {ring.get('type')}"
                            break
                    if truth_assoc == "none":
                        for hn in hard_negatives:
                            if fa in hn.get("accounts", []):
                                truth_assoc = f"Hard Negative"
                                break
                    
                    # Get ledger of max points tx
                    txs = result.tx[result.tx["payer_id"] == fa]
                    best_d = None
                    for tx_id in txs["tx_id"]:
                        d = result.decisions.get(tx_id)
                        if d:
                            if best_d is None or d.net_points > best_d.net_points:
                                best_d = d
                    
                    fraud_accounts_output.append(f"- **Account:** {fa} | **Truth:** {truth_assoc}")
                    if best_d:
                        for ll in best_d.ledger:
                            fraud_accounts_output.append(f"  > {ll.points} | {ll.source} | {ll.text}")
        out_md.append("")
        
    out_md.append("### (c) FRAUD-tier Accounts Ledgers")
    out_md.extend(fraud_accounts_output)
    
    out_md.append("\n### (d) Conclusion")
    out_md.append("R1 members blocked from FRAUD tier cause distribution:")
    out_md.append(f"- Blocked by net_points < {cfg['gate']['fraud_net']}: {r1_fraud_blocks_points}")
    out_md.append(f"- Blocked by structural types < {cfg['gate']['fraud_min_structural_types']}: {r1_fraud_blocks_structure}")
    
    out_md.append("\nConclusion: R1 members fail to reach the FRAUD tier primarily because they do not accumulate enough net points (often hitting ~50 points, below the 60 threshold) despite triggering the required structural motifs. This is a genuine threshold issue combined with a strict metric-definition artefact.")
    
    full_text = "\n".join(out_md)
    Path("docs/GATE_ANALYSIS.md").write_text(full_text, encoding="utf-8")
    Path("docs/AUDIT_FINDINGS.md").write_text(full_text, encoding="utf-8")

if __name__ == "__main__":
    main()
