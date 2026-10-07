import streamlit as st
import sys
from pathlib import Path

# Ensure src is in pythonpath
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from ui import theme

st.set_page_config(page_title="TRACE-FX", layout="wide", page_icon="🛡️")
theme.apply_theme()

pg = st.navigation([
    st.Page("pages/01_mission_control.py", title="MISSION CONTROL", icon="🚀"),
    st.Page("pages/02_detection_quality.py", title="DETECTION QUALITY", icon="📊"),
    st.Page("pages/03_investigate.py", title="INVESTIGATE", icon="🔍"),
    st.Page("pages/04_fraud_networks.py", title="FRAUD NETWORKS", icon="🕸️"),
    st.Page("pages/05_temporal_replay.py", title="TEMPORAL REPLAY", icon="⏱️"),
    st.Page("pages/06_how_tracefx_works.py", title="HOW TRACE-FX WORKS", icon="⚙️"),
    st.Page("pages/07_data_and_system.py", title="DATA & SYSTEM", icon="📂"),
])

pg.run()
