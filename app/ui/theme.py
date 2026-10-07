import streamlit as st

def apply_theme():
    """Inject CSS variables for TRACE-FX Security Operations Theme."""
    st.markdown("""
    <style>
        /* CSS Variables for Dark Modern Theme */
        :root {
            --bg: #0B0F17;
            --surface: #121826;
            --surface-hover: #1F2937;
            --border: #1F2937;
            --text: #E6EAF2;
            --text-muted: #8B95A7;
            --accent-cyan: #22D3EE;
            
            --fraud: #F43F5E;
            --review: #F59E0B;
            --clear: #10B981;
            --ring: #8B5CF6;
        }

        /* Base Typography */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: var(--text);
            background-color: var(--bg);
        }
        
        /* Monospace elements */
        .mono {
            font-family: 'JetBrains Mono', monospace;
        }
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {
            color: var(--text);
            font-weight: 600;
            letter-spacing: -0.02em;
        }
        
        /* Cards */
        .stCard {
            background-color: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        
        /* Badges */
        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .badge-fraud { background: rgba(244, 63, 94, 0.15); color: var(--fraud); border: 1px solid rgba(244, 63, 94, 0.3); }
        .badge-review { background: rgba(245, 158, 11, 0.15); color: var(--review); border: 1px solid rgba(245, 158, 11, 0.3); }
        .badge-clear { background: rgba(16, 185, 129, 0.15); color: var(--clear); border: 1px solid rgba(16, 185, 129, 0.3); }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: var(--surface);
            border-right: 1px solid var(--border);
        }
        
        /* Hide default Streamlit clutter */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Tooltip style */
        .tooltip {
            position: relative;
            display: inline-block;
            border-bottom: 1px dotted var(--text-muted);
            cursor: help;
        }
        
        /* Progress bars */
        .stProgress > div > div > div > div {
            background-color: var(--accent-cyan);
        }
        
        /* Table enhancements */
        [data-testid="stDataFrame"] {
            background-color: var(--surface);
            border-radius: 8px;
            border: 1px solid var(--border);
        }
    </style>
    """, unsafe_allow_html=True)
