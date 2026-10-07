import pandas as pd
import json
import uuid
import ipaddress
import numpy as np
from pathlib import Path

def process_ecommerce():
    raw_path = Path("data/Traindata/Fraud_Data.csv")
    ip_path = Path("data/Traindata/IpAddress_to_Country.csv")
    out_dir = Path("data/external")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not raw_path.exists() or not ip_path.exists():
        print(f"Skipping: Missing files in data/Traindata/")
        return
        
    df = pd.read_csv(raw_path)
    # The requirement is just joining or we can just ignore country if not requested.
    # The prompt says: "Input: Fraud_Data.csv & IpAddress_to_Country.csv. Output: ecommerce_raw.csv (the joined df)"
    df_ip = pd.read_csv(ip_path)
    
    # Fast IP join approach
    # Sort ip_address ranges
    # Since IP datasets can be large, we'll use merge_asof
    df_ip = df_ip.sort_values("lower_bound_ip_address")
    
    df_sorted = df.sort_values("ip_address").copy()
    
    joined = pd.merge_asof(
        df_sorted, df_ip,
        left_on="ip_address", right_on="lower_bound_ip_address",
        direction="backward"
    )
    # Validate upper bound
    joined["country"] = np.where(
        joined["ip_address"] <= joined["upper_bound_ip_address"],
        joined["country"],
        "UNKNOWN"
    )
    
    # We must sort back to original or just keep it
    joined.to_csv(out_dir / "ecommerce_raw.csv", index=False)
    
    # Now canonicalize
    canon = pd.DataFrame()
    # Generate UUIDs
    canon["tx_id"] = [str(uuid.uuid4()) for _ in range(len(joined))]
    
    # ts: purchase_time -> UTC ISO
    # pandas to_datetime -> ISO
    canon["ts"] = pd.to_datetime(joined["purchase_time"]).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    canon["payer_id"] = joined["user_id"].astype(str)
    canon["payee_id"] = "MERCH_EXTERNAL"
    canon["amount"] = joined["purchase_value"].astype(float)
    canon["tx_type"] = "MERCHANT"
    canon["device_id"] = joined["device_id"].astype(str)
    canon["ip"] = joined["ip_address"].astype(str)
    canon["label"] = joined["class"].apply(lambda x: "FRAUD" if x == 1 else "LEGIT")
    
    # Save canonical
    canon.to_csv(out_dir / "ecommerce_canonical.csv", index=False)
    
    # Save truth
    fraud_txs = canon[canon["label"] == "FRAUD"]["tx_id"].tolist()
    truth = {
        "dataset": "ecommerce",
        "is_fraud_tx_ids": fraud_txs,
        "rings": [],
        "hard_negatives": []
    }
    
    with open(out_dir / "ecommerce_truth.json", "w") as f:
        json.dump(truth, f, indent=2)
        
    print(f"E-commerce converted: {len(canon)} rows. {len(fraud_txs)} fraud txs.")

if __name__ == "__main__":
    process_ecommerce()
