import streamlit as st
import networkx as nx
import plotly.graph_objects as go
import pandas as pd

st.title("FRAUD NETWORKS")
st.markdown("Visualized networks of coordinated suspicious activity. Ring topology explains the structural layout of detected motifs.")

if "run_result" not in st.session_state or st.session_state.run_result is None:
    st.warning("Run TRACE-FX before opening an investigation.")
    st.stop()

res = st.session_state.run_result

if not res.groups:
    st.info("No suspicious networks found.")
    st.stop()

# Group selection
cols = st.columns([1, 2])
with cols[0]:
    st.markdown("### Discovered Networks")
    g_ids = [g.group_id for g in res.groups]
    sel_g = st.radio("Select Ring", g_ids, label_visibility="collapsed")
    
    group = next(g for g in res.groups if g.group_id == sel_g)
    
    st.markdown(f"**RING ID**: `{sel_g}`")
    st.markdown(f"**Accounts**: {len(group.accounts)}")
    st.markdown(f"**Risk**: {group.risk:.2f}")
    st.markdown(f"**Shape**: {group.shape}")
    
    ev_chips = " ".join([f"<span class='badge' style='background:var(--ring); color:white;'>{e}</span>" for e in group.evidence_types])
    st.markdown(f"**Patterns**: {ev_chips}", unsafe_allow_html=True)
    
    if st.button("OPEN INVESTIGATION", type="primary"):
        st.session_state.investigate_target = group.accounts[0]
        st.switch_page("pages/03_investigate.py")

with cols[1]:
    st.markdown("### Ring Topology")
    
    nodes_in_ring = set(group.accounts)
    
    g_edges = []
    for e in res.graph["edges"]:
        if e["from"] in nodes_in_ring or e["to"] in nodes_in_ring:
            g_edges.append(e)
            nodes_in_ring.add(e["from"])
            nodes_in_ring.add(e["to"])
            
    G = nx.Graph()
    for n in res.graph["nodes"]:
        if n["id"] in nodes_in_ring:
            G.add_node(n["id"], **n)
            
    for e in g_edges:
        G.add_edge(e["from"], e["to"], **e)
        
    if len(G.nodes) == 0:
        st.warning("No graph data available for this ring.")
    else:
        pos = nx.spring_layout(G, seed=42)
        
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1, color='#8B95A7'),
            hoverinfo='none',
            mode='lines'
        )
        
        node_x = []
        node_y = []
        node_text = []
        node_color = []
        node_size = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            ndata = G.nodes[node]
            ntype = ndata.get("type", "unknown").upper()
            label = ndata.get("decision", "")
            
            node_text.append(f"{ntype}: {node}<br>{label}")
            
            if label == "FRAUD": c = '#F43F5E'
            elif label == "REVIEW": c = '#F59E0B'
            elif label == "LEGIT": c = '#10B981'
            else: c = '#22D3EE' # device/wallet
            node_color.append(c)
            
            node_size.append(25 if ntype == 'ACCOUNT' else 15)
                
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=[G.nodes[n].get("label", "") for n in G.nodes()],
            textposition="top center",
            hovertext=node_text,
            marker=dict(
                showscale=False,
                color=node_color,
                size=node_size,
                line=dict(width=2, color='#1F2937')
            )
        )
        
        fig = go.Figure(data=[edge_trace, node_trace],
             layout=go.Layout(
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0,l=0,r=0,t=0),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
             )
        )
        
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("### Structural Explanations")
st.info("SOURCE ACCOUNTS ↓ SHARED INFRASTRUCTURE ↓ SINK ↓ PASS-THROUGH ↓ DESTINATION")
