import streamlit as st
import pandas as pd
from ui import datasets
import os
from pathlib import Path

st.title("DATA & SYSTEM")
st.markdown("Dataset registry, capability mapping, and real-time system status.")

st.markdown("### Dataset Registry")
registry_list = datasets.discover_datasets()
registry = {d["name"]: d for d in registry_list}

if not registry:
    st.warning("No datasets discovered.")
else:
    rows = []
    for name, ds in registry.items():
        meta = datasets.load_dataset_metadata(ds["path"])
        
        # Categorize
        cat = "DEMO DATA"
        if "hybrid" in name.lower(): cat = "HYBRID DATA"
        elif "Traindata" in ds["path"]: cat = "REAL DATA (Raw)"
        elif "external" in ds["path"]: cat = "REAL DATA (Mapped)"
        
        rows.append({
            "Name": name,
            "Type": cat,
            "Status": "READY" if meta.get("rows", 0) > 0 else "PENDING",
            "Rows": meta.get("rows", "Unknown"),
            "Accounts": meta.get("accounts", "Unknown"),
            "Time Range": meta.get("time_range", "Unknown"),
            "Labels": "✅" if meta.get("has_truth") else "❌",
            "Capabilities": ", ".join([k for k,v in meta.get("capabilities", {}).items() if v])
        })
        
    df_reg = pd.DataFrame(rows)
    st.dataframe(df_reg, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("### IEEE / External Raw Data Status (`data/Traindata/`)")

traindata_dir = Path("data/Traindata")
if not traindata_dir.exists():
    st.info("Directory `data/Traindata/` not found. External raw data mapping is inactive.")
else:
    files = list(traindata_dir.glob("*.csv"))
    if not files:
        st.info("No raw CSVs found in `data/Traindata/`.")
    else:
        for f in files:
            size_mb = f.stat().st_size / (1024 * 1024)
            st.markdown(f"- **File**: `{f.name}` ({size_mb:.1f} MB) - Awaiting/Processed via `tools/external_ecommerce.py`")
            
st.markdown("---")
st.markdown("### System Hardware & Environment")
st.markdown(f"- **OS**: Windows")
st.markdown(f"- **Python Runtime**: Offline, Local CPU")
st.markdown(f"- **Engine State**: Deterministic Execution Mode")
st.markdown(f"- **Streamlit Version**: {st.__version__}")
