"""Replay HTML generator for TRACE-FX.

Generates a self-contained offline HTML file with a time-slider
that shows evidence accumulating and the fraud alert firing.

Uses vendored vis-network from app/assets/.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .types import Result

log = logging.getLogger(__name__)

# Path to vendored vis-network
_ASSETS_DIR = Path(__file__).parent.parent.parent / "app" / "assets"


def build_html(result: Result) -> str:
    """Render a self-contained replay HTML string.

    Args:
        result: Pipeline Result.

    Returns:
        HTML string.
    """
    # Load vendored vis-network CSS and JS
    vis_css = _load_asset("vis-network.min.css", "/* vis-network CSS not found */")
    vis_js = _load_asset("vis-network.min.js", "// vis-network JS not found")

    # Build timeline events for the replay
    graph_data = result.graph
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    # Serialize for JS
    nodes_json = json.dumps(nodes, default=str)
    edges_json = json.dumps(edges, default=str)

    # Alert timestamps
    alert_times = []
    for acc, dec in result.decisions.items():
        if dec.label == "FRAUD" and dec.alert_ts:
            alert_times.append(dec.alert_ts)

    alerts_json = json.dumps(alert_times)

    # Evidence timeline
    evidence_events = []
    for ev in result.evidence:
        evidence_events.append({
            "type": ev.type,
            "accounts": list(ev.accounts),
            "satisfied_at": ev.satisfied_at,
            "strength": ev.strength,
            "detail": ev.detail,
        })
    evidence_json = json.dumps(evidence_events, default=str)

    html = _HTML_TEMPLATE.format(
        vis_css=vis_css,
        vis_js=vis_js,
        nodes_json=nodes_json,
        edges_json=edges_json,
        alerts_json=alerts_json,
        evidence_json=evidence_json,
        n_transactions=result.metrics.get("total_transactions", 0),
        n_accounts=result.metrics.get("total_accounts", 0),
        elapsed_s=result.metrics.get("elapsed_s", 0),
    )

    return html


def _load_asset(filename: str, fallback: str) -> str:
    """Load a vendored asset file."""
    asset_path = _ASSETS_DIR / filename
    if asset_path.exists():
        return asset_path.read_text(encoding="utf-8", errors="replace")
    log.warning("Asset not found: %s (using fallback)", asset_path)
    return fallback


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TRACE-FX Causal Replay</title>
  <style>
{vis_css}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #0f1117;
      color: #e0e0e0;
    }}
    #header {{
      padding: 16px 24px;
      background: #1a1d27;
      border-bottom: 1px solid #2d3142;
      display: flex;
      align-items: center;
      gap: 16px;
    }}
    #header h1 {{
      font-size: 1.2rem;
      font-weight: 700;
      color: #f0f0f0;
    }}
    #header .badge {{
      padding: 3px 10px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }}
    .badge-fraud {{ background: #dc2626; color: white; }}
    .badge-info {{ background: #2d3142; color: #9ca3af; }}
    #controls {{
      padding: 12px 24px;
      background: #13151f;
      border-bottom: 1px solid #2d3142;
      display: flex;
      align-items: center;
      gap: 16px;
    }}
    #timeline-slider {{
      flex: 1;
      height: 6px;
      accent-color: #f59e0b;
    }}
    #time-display {{
      font-size: 0.85rem;
      color: #9ca3af;
      min-width: 220px;
    }}
    #play-btn {{
      padding: 6px 16px;
      background: #f59e0b;
      color: #0f1117;
      border: none;
      border-radius: 6px;
      font-weight: 700;
      cursor: pointer;
      font-size: 0.85rem;
    }}
    #play-btn:hover {{ background: #d97706; }}
    #main {{
      display: flex;
      height: calc(100vh - 110px);
    }}
    #network {{
      flex: 1;
    }}
    #sidebar {{
      width: 320px;
      background: #1a1d27;
      border-left: 1px solid #2d3142;
      overflow-y: auto;
      padding: 16px;
    }}
    .ev-item {{
      padding: 10px;
      margin-bottom: 8px;
      border-radius: 6px;
      border-left: 3px solid #2d3142;
      font-size: 0.82rem;
    }}
    .ev-item.active {{
      border-left-color: #f59e0b;
      background: #1e2235;
    }}
    .ev-type {{
      font-weight: 700;
      color: #f59e0b;
      text-transform: uppercase;
      font-size: 0.75rem;
    }}
    .ev-detail {{ color: #9ca3af; margin-top: 4px; }}
    #alert-banner {{
      display: none;
      padding: 12px 24px;
      background: #dc2626;
      color: white;
      font-weight: 700;
      text-align: center;
      font-size: 0.95rem;
      animation: pulse 1s ease-in-out 3;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.7; }}
    }}
  </style>
</head>
<body>
<div id="header">
  <h1>TRACE-FX — Causal Replay</h1>
  <span class="badge badge-info">{n_transactions:,} transactions</span>
  <span class="badge badge-info">{n_accounts:,} accounts</span>
  <span class="badge badge-info">Scored in {elapsed_s:.2f}s</span>
</div>
<div id="alert-banner">🚨 FRAUD ALERT FIRED — Gate conditions met at this timestamp</div>
<div id="controls">
  <button id="play-btn" onclick="togglePlay()">▶ Play</button>
  <input type="range" id="timeline-slider" min="0" max="1000" value="0"
         oninput="onSlider(this.value)">
  <div id="time-display">Slide to replay timeline</div>
</div>
<div id="main">
  <div id="network"></div>
  <div id="sidebar">
    <h3 style="color:#f0f0f0;margin-bottom:12px;font-size:0.9rem;">Evidence Timeline</h3>
    <div id="ev-list"></div>
  </div>
</div>

<script>
{vis_js}
</script>
<script>
const ALL_NODES = {nodes_json};
const ALL_EDGES = {edges_json};
const ALERT_TIMES = {alerts_json};
const EVIDENCE = {evidence_json};

// Parse timestamps
function parseTs(ts) {{
  try {{ return new Date(ts).getTime(); }} catch(e) {{ return 0; }}
}}

const tsList = ALL_NODES.map(n => parseTs(n.satisfied_at || "")).filter(t => t > 0);
const minT = tsList.length > 0 ? Math.min(...tsList) : Date.now() - 86400000;
const maxT = tsList.length > 0 ? Math.max(...tsList) : Date.now();

// Colors per decision
const COLORS = {{
  FRAUD: {{ background: '#dc2626', border: '#991b1b', font: '#fff' }},
  REVIEW: {{ background: '#d97706', border: '#92400e', font: '#fff' }},
  LEGIT: {{ background: '#374151', border: '#4b5563', font: '#9ca3af' }},
  EVIDENCE: {{ background: '#1d4ed8', border: '#1e40af', font: '#fff' }},
  SINK: {{ background: '#7c3aed', border: '#5b21b6', font: '#fff' }},
  device: {{ background: '#0369a1', border: '#0284c7', font: '#fff' }},
  wallet: {{ background: '#6d28d9', border: '#5b21b6', font: '#fff' }},
}};

// vis-network setup
const container = document.getElementById('network');
const nodeDataSet = new vis.DataSet([]);
const edgeDataSet = new vis.DataSet([]);
const network = new vis.Network(container, {{ nodes: nodeDataSet, edges: edgeDataSet }}, {{
  physics: {{ enabled: true, stabilization: {{ iterations: 100 }}, barnesHut: {{ gravitationalConstant: -5000 }} }},
  edges: {{ arrows: {{ to: {{ enabled: true, scaleFactor: 0.5 }} }}, color: {{ color: '#4b5563', highlight: '#f59e0b' }}, smooth: {{ type: 'curvedCW', roundness: 0.2 }} }},
  nodes: {{ shape: 'dot', size: 18, font: {{ color: '#e0e0e0', size: 12 }}, borderWidth: 2 }},
  interaction: {{ hover: true, tooltipDelay: 200 }},
}});

function colorForNode(n) {{
  if (n.type === 'device') return COLORS.device;
  if (n.type === 'wallet') return COLORS.wallet;
  return COLORS[n.decision] || COLORS.LEGIT;
}}

function updateGraph(currentT) {{
  // Show nodes that are satisfied by currentT
  const visibleNodes = ALL_NODES.filter(n => {{
    const t = parseTs(n.satisfied_at || "");
    return t === 0 || t <= currentT;
  }});
  const visibleIds = new Set(visibleNodes.map(n => n.id));
  const visibleEdges = ALL_EDGES.filter(e => {{
    const t = parseTs(e.satisfied_at || "");
    return (t === 0 || t <= currentT) && visibleIds.has(e.from) && visibleIds.has(e.to);
  }});

  nodeDataSet.clear();
  edgeDataSet.clear();

  nodeDataSet.add(visibleNodes.map(n => {{
    const c = colorForNode(n);
    return {{ id: n.id, label: n.label || n.id.slice(-8), color: c, title: n.decision + ' | risk: ' + (n.risk || 0).toFixed(2) }};
  }}));
  edgeDataSet.add(visibleEdges.map((e, i) => ({{
    id: 'e' + i,
    from: e.from,
    to: e.to,
    label: e.type,
    color: {{ color: e.type.includes('device') ? '#0369a1' : e.type.includes('sink') ? '#7c3aed' : '#4b5563' }},
    width: 1 + (e.strength || 0) * 2,
  }})));
}}

function updateEvList(currentT) {{
  const list = document.getElementById('ev-list');
  list.innerHTML = '';
  EVIDENCE.forEach(ev => {{
    const t = parseTs(ev.satisfied_at);
    const active = t > 0 && t <= currentT;
    const div = document.createElement('div');
    div.className = 'ev-item' + (active ? ' active' : '');
    div.innerHTML = '<div class="ev-type">' + ev.type.replace(/_/g,' ') + '</div>' +
      '<div class="ev-detail">' + (ev.satisfied_at || '') + '<br>' +
      ev.accounts.slice(0,3).join(', ') + (ev.accounts.length > 3 ? '...' : '') + '</div>';
    list.appendChild(div);
  }});
}}

function checkAlert(currentT) {{
  const banner = document.getElementById('alert-banner');
  const fired = ALERT_TIMES.some(ts => parseTs(ts) <= currentT);
  banner.style.display = fired ? 'block' : 'none';
}}

function onSlider(val) {{
  const frac = val / 1000;
  const currentT = minT + frac * (maxT - minT);
  const d = new Date(currentT);
  document.getElementById('time-display').textContent = d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  updateGraph(currentT);
  updateEvList(currentT);
  checkAlert(currentT);
}}

// Auto-play
let playing = false;
let playInterval = null;
let sliderVal = 0;

function togglePlay() {{
  playing = !playing;
  document.getElementById('play-btn').textContent = playing ? '⏸ Pause' : '▶ Play';
  if (playing) {{
    playInterval = setInterval(() => {{
      sliderVal = Math.min(sliderVal + 5, 1000);
      document.getElementById('timeline-slider').value = sliderVal;
      onSlider(sliderVal);
      if (sliderVal >= 1000) {{ clearInterval(playInterval); playing = false; document.getElementById('play-btn').textContent = '▶ Play'; sliderVal = 0; }}
    }}, 50);
  }} else {{
    if (playInterval) clearInterval(playInterval);
  }}
}}

// Initial render
updateGraph(minT);
updateEvList(minT);
</script>
</body>
</html>
"""
