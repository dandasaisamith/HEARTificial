import streamlit as st
import networkx as nx
import plotly.graph_objects as go
import pandas as pd

st.title("Fraud Rings")
st.markdown("Visualized networks of coordinated suspicious activity.")

if "run_result" not in st.session_state or st.session_state.run_result is None:
    st.warning("Please run a dataset in Mission Control first.")
    st.stop()

res = st.session_state.run_result

if not res.groups:
    st.info("No suspicious rings found.")
    st.stop()

# Group selection
cols = st.columns([1, 3])
with cols[0]:
    st.markdown("### Discovered Networks")
    g_ids = [g.group_id for g in res.groups]
    sel_g = st.radio("Select Ring", g_ids, label_visibility="collapsed")
    
    group = next(g for g in res.groups if g.group_id == sel_g)
    
    st.markdown(f"**Ring**: {sel_g}")
    st.markdown(f"**Size**: {len(group.accounts)} accounts")
    st.markdown(f"**Shape**: {group.shape}")
    st.markdown(f"**Risk**: {group.risk:.2f}")
    st.markdown("**Evidence**:")
    for ev in group.evidence_types:
        st.markdown(f"<span class='badge' style='background:var(--ring); color:white;'>{ev}</span>", unsafe_allow_html=True)

with cols[1]:
    st.markdown("### Ring Topology")
    
    # Filter graph to just this ring's neighborhood
    nodes_in_ring = set(group.accounts)
    
    # Find relevant edges from res.graph
    g_edges = []
    for e in res.graph["edges"]:
        if e["from"] in nodes_in_ring or e["to"] in nodes_in_ring:
            g_edges.append(e)
            nodes_in_ring.add(e["from"])
            nodes_in_ring.add(e["to"])
            
    # Build NetworkX graph for layout
    G = nx.Graph()
    for n in res.graph["nodes"]:
        if n["id"] in nodes_in_ring:
            G.add_node(n["id"], **n)
            
    for e in g_edges:
        G.add_edge(e["from"], e["to"], **e)
        
    if len(G.nodes) == 0:
        st.warning("No graph data available for this ring.")
    else:
        # Compute layout once
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
        node_line_width = []
        node_line_color = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            ndata = G.nodes[node]
            ntype = ndata.get("type", "unknown")
            label = ndata.get("decision", "")
            
            node_text.append(f"{ntype.upper()}: {node}<br>Decision: {label}")
            
            # Colors
            if label == "FRAUD": c = '#F43F5E'
            elif label == "REVIEW": c = '#F59E0B'
            elif label == "LEGIT": c = '#10B981'
            else: c = '#22D3EE' # device/wallet
            node_color.append(c)
            
            node_size.append(25 if ntype == 'account' else 15)
            
            if node in group.accounts:
                node_line_width.append(3)
                node_line_color.append('#8B5CF6') # Ring violet
            else:
                node_line_width.append(1)
                node_line_color.append('#1F2937')
                
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
                line=dict(width=node_line_width, color=node_line_color)
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
