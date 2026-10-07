import json
import uuid
import random
import pandas as pd
from pathlib import Path
from datetime import timedelta

def generate_hybrid_seed():
    in_csv = Path("data/external/ecommerce_40k.csv")
    in_truth = Path("data/external/ecommerce_truth.json")
    out_csv = Path("data/external/hybrid_seed.csv")
    out_truth = Path("data/external/truth_hybrid_seed.json")
    
    if not in_csv.exists() or not in_truth.exists():
        print("Missing 40k sub-sample or truth.")
        return
        
    df = pd.read_csv(in_csv)
    with open(in_truth) as f:
        truth = json.load(f)
        
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    min_ts = df["ts"].min()
    max_ts = df["ts"].max()
    
    new_rows = []
    rings = []
    hybrid_is_fraud_tx_ids = set(truth.get("is_fraud_tx_ids", []))
    
    # We want to inject 3 R1 rings. 
    # R1: shared device + pass-through + burst
    for r in range(3):
        n_accounts = random.randint(4, 6)
        accounts = [f"HYBRID_U_{r}_{i}" for i in range(n_accounts)]
        device_id = f"HYBRID_DEV_{r}"
        
        # Pick a random anchor time within the range
        delta = (max_ts - min_ts).total_seconds()
        anchor_ts = min_ts + timedelta(seconds=random.uniform(0, delta - 3600))
        
        # Pass-through: A -> B -> C
        for i in range(n_accounts - 1):
            payer = accounts[i]
            payee = accounts[i+1]
            tx_id = f"HYBRID_TX_{r}_{i}"
            ts_str = (anchor_ts + timedelta(minutes=i*5)).strftime('%Y-%m-%dT%H:%M:%SZ')
            
            new_rows.append({
                "tx_id": tx_id,
                "ts": ts_str,
                "payer_id": payer,
                "payee_id": payee,
                "amount": round(random.uniform(500, 2000), 2),
                "tx_type": "P2P",
                "device_id": device_id,
                "ip": "1.1.1.1",
                "label": "FRAUD"
            })
            hybrid_is_fraud_tx_ids.add(tx_id)
            
        rings.append({
            "type": "R1",
            "accounts": accounts
        })
        
    # Append to dataframe
    df_new = pd.DataFrame(new_rows)
    df_new["ts"] = pd.to_datetime(df_new["ts"], utc=True)
    
    df_comb = pd.concat([df, df_new], ignore_index=True)
    df_comb = df_comb.sort_values("ts")
    df_comb["ts"] = df_comb["ts"].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    df_comb.to_csv(out_csv, index=False)
    
    truth["is_fraud_tx_ids"] = list(hybrid_is_fraud_tx_ids)
    truth["rings"] = rings
    truth["dataset"] = "hybrid_ecommerce"
    
    with open(out_truth, "w") as f:
        json.dump(truth, f, indent=2)
        
    print(f"Hybrid seed created: {len(df_comb)} rows ({len(new_rows)} synthetic injected).")
    print(f"Injected {len(rings)} R1 rings.")

if __name__ == "__main__":
    generate_hybrid_seed()
