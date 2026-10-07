import streamlit as st
import sys
from pathlib import Path

# Ensure src is in pythonpath
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ui import theme

st.set_page_config(page_title="TRACE-FX", layout="wide", page_icon="🛡️")
theme.apply_theme()

pg1 = st.Page("pages/01_mission_control.py", title="Mission Control", icon="🚀")
pg2 = st.Page("pages/02_scorecard.py", title="Accuracy Scorecard", icon="📊")
pg3 = st.Page("pages/03_case_queue.py", title="Case Queue", icon="🔍")
pg4 = st.Page("pages/04_fraud_rings.py", title="Fraud Rings", icon="🕸️")
pg5 = st.Page("pages/05_replay.py", title="Temporal Replay", icon="⏱️")
pg6 = st.Page("pages/06_how_it_works.py", title="How it Works & PS04", icon="💡")

pg = st.navigation([pg1, pg2, pg3, pg4, pg5, pg6])
pg.run()
