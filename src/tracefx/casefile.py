"""Case file renderer for TRACE-FX.

Renders a per-group HTML case file using Jinja2.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .types import Group, Result

log = logging.getLogger(__name__)

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>TRACE-FX Case File — {{ group.group_id }}</title>
  <style>
    body { font-family: -apple-system, sans-serif; background: #0f1117; color: #e0e0e0; padding: 24px; }
    h1 { color: #f59e0b; }
    h2 { color: #9ca3af; font-size: 0.95rem; text-transform: uppercase; margin-top: 24px; }
    .badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .badge-fraud { background: #dc2626; }
    .badge-review { background: #d97706; }
    .badge-legit { background: #374151; color: #9ca3af; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th { background: #1a1d27; padding: 8px 12px; text-align: left; font-size: 0.8rem; color: #9ca3af; }
    td { padding: 8px 12px; border-bottom: 1px solid #2d3142; font-size: 0.82rem; }
    .positive { color: #f59e0b; }
    .negative { color: #34d399; }
  </style>
</head>
<body>
  <h1>Case File: {{ group.group_id }}</h1>
  <p>
    <span class="badge badge-{{ group_label | lower }}">{{ group_label }}</span>
    &nbsp; Risk: {{ "%.2f" | format(group.risk) }} &nbsp; Shape: {{ group.shape }}
  </p>
  <p style="color:#9ca3af; margin-top:8px;">{{ group.summary }}</p>

  <h2>Accounts ({{ group.accounts | length }})</h2>
  <table>
    <tr><th>Account</th><th>Label</th><th>Risk</th><th>Net Points</th><th>Alert Time</th></tr>
    {% for acc in group.accounts %}
    <tr>
      <td>{{ acc }}</td>
      <td>
        {% if decisions[acc] is defined %}
          <span class="badge badge-{{ decisions[acc].label | lower }}">{{ decisions[acc].label }}</span>
        {% else %} — {% endif %}
      </td>
      <td>{% if decisions[acc] is defined %}{{ "%.4f" | format(decisions[acc].risk) }}{% else %}—{% endif %}</td>
      <td>{% if decisions[acc] is defined %}{{ "%.1f" | format(decisions[acc].net_points) }}{% else %}—{% endif %}</td>
      <td style="font-size:0.75rem;">{% if decisions[acc] is defined %}{{ decisions[acc].alert_ts }}{% else %}—{% endif %}</td>
    </tr>
    {% endfor %}
  </table>

  <h2>Evidence ({{ evidence | length }} items)</h2>
  {% for ev in evidence %}
  <div style="margin-bottom:12px; padding:12px; background:#1a1d27; border-radius:6px; border-left:3px solid #f59e0b;">
    <div style="font-weight:700; color:#f59e0b;">{{ ev.type | upper }}</div>
    <div style="font-size:0.82rem; color:#9ca3af; margin-top:4px;">
      Satisfied at: {{ ev.satisfied_at }}<br>
      Strength: {{ "%.2f" | format(ev.strength) }}<br>
      Accounts: {{ ev.accounts | join(', ') }}<br>
      Supporting tx: {{ ev.tx_ids[:5] | join(', ') }}{% if ev.tx_ids | length > 5 %}...{% endif %}
    </div>
  </div>
  {% endfor %}

  <h2>Evidence Ledger (first account)</h2>
  {% if group.accounts and decisions[group.accounts[0]] is defined %}
  <table>
    <tr><th>Source</th><th>Points</th><th>Evidence</th></tr>
    {% for line in decisions[group.accounts[0]].ledger %}
    <tr>
      <td>{{ line.source }}</td>
      <td class="{{ 'positive' if line.points > 0 else 'negative' }}">{{ "%.1f" | format(line.points) }}</td>
      <td style="font-size:0.8rem;">{{ line.text }}</td>
    </tr>
    {% endfor %}
  </table>
  {% endif %}
</body>
</html>
"""


def render(result: Result, group_id: str) -> str:
    """Render a case file HTML for a fraud group.

    Args:
        result: Pipeline Result.
        group_id: ID of the group to render.

    Returns:
        HTML string.
    """
    try:
        from jinja2 import Environment
    except ImportError:
        log.error("Jinja2 not available for casefile rendering")
        return "<html><body>Jinja2 not available</body></html>"

    group = next((g for g in result.groups if g.group_id == group_id), None)
    if group is None:
        return f"<html><body>Group {group_id} not found</body></html>"

    # Get relevant evidence
    evidence = [ev for ev in result.evidence if any(acc in group.accounts for acc in ev.accounts)]

    # Determine group label
    decisions = result.decisions
    group_label = "LEGIT"
    for acc in group.accounts:
        if acc in decisions:
            lbl = decisions[acc].label
            if lbl == "FRAUD":
                group_label = "FRAUD"
                break
            elif lbl == "REVIEW":
                group_label = "REVIEW"

    env = Environment(autoescape=True)
    template = env.from_string(_TEMPLATE)

    return template.render(
        group=group,
        group_label=group_label,
        evidence=evidence,
        decisions=decisions,
    )
