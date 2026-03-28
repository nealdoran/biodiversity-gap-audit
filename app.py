"""
Global Biodiversity Data Gap Audit
Streamlit Dashboard
Built by Neal Doran, Ph.D. | Bio Database v2

Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Biodiversity Data Gap Audit",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Arial');
    html, body, [class*="css"] { font-family: Arial, sans-serif; }
    .main { background-color: #ffffff; }
    .metric-card {
        background: #f8f9fa;
        border-left: 4px solid #c0392b;
        padding: 16px 20px;
        border-radius: 4px;
        margin-bottom: 8px;
    }
    .metric-value { font-size: 2.2rem; font-weight: bold; color: #c0392b; }
    .metric-label { font-size: 0.85rem; color: #666; margin-top: 2px; }
    .metric-card.teal { border-left-color: #1abc9c; }
    .metric-card.teal .metric-value { color: #1abc9c; }
    .metric-card.blue { border-left-color: #1F4E79; }
    .metric-card.blue .metric-value { color: #1F4E79; }
    footer { color: #999; font-size: 0.78rem; }
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def load_data():
    df = pd.read_csv(os.path.join(BASE_DIR, "cr_audit_data.csv"))
    cs = pd.read_csv(os.path.join(BASE_DIR, "class_summary.csv"))
    # Clean nulls
    df['class']           = df['class'].fillna('Unknown')
    df['order_name']      = df['order_name'].fillna('Unknown')
    df['family']          = df['family'].fillna('Unknown')
    df['population_trend']= df['population_trend'].fillna('Unknown')
    return df, cs

df, class_summary = load_data()

# ── Header ────────────────────────────────────────────────────────
st.markdown("## 🌿 Global Biodiversity Data Gap Audit")
st.markdown(
    "**Cross-audit of IUCN Red List × GBIF Occurrence Data &nbsp;|&nbsp; 26 Million Records**"
)
st.caption("Built by Neal Doran, Ph.D. &nbsp;|&nbsp; Bio Database v2 &nbsp;|&nbsp; bio_database_v2.db")
st.divider()

# ── Sidebar filters ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filters")

    # Category
    cat_options = ["All"] + sorted(df['category'].unique().tolist(),
                                    key=lambda x: ['CR','EN','VU','NT'].index(x)
                                    if x in ['CR','EN','VU','NT'] else 99)
    selected_cat = st.selectbox("IUCN Category", cat_options, index=0)

    # Class
    class_options = ["All"] + sorted(df['class'].unique().tolist())
    selected_class = st.selectbox("Taxonomic Class", class_options, index=0)

    # Occurrence threshold
    threshold = st.slider(
        "Data gap threshold (max occurrences)",
        min_value=0, max_value=100, value=10, step=1,
        help="Species with fewer than this many GBIF records are flagged as data gaps"
    )

    st.divider()
    st.markdown("**Category legend**")
    st.markdown("🔴 **CR** — Critically Endangered")
    st.markdown("🟠 **EN** — Endangered")
    st.markdown("🟡 **VU** — Vulnerable")
    st.markdown("🔵 **NT** — Near Threatened")

# ── Filter data ───────────────────────────────────────────────────
filtered = df.copy()
if selected_cat != "All":
    filtered = filtered[filtered['category'] == selected_cat]
if selected_class != "All":
    filtered = filtered[filtered['class'] == selected_class]

gap_df = filtered[filtered['total_occurrences'] < threshold]

# ── Metric cards ──────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f"""
    <div class="metric-card blue">
        <div class="metric-value">{len(filtered):,}</div>
        <div class="metric-label">Species in current selection</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{len(gap_df):,}</div>
        <div class="metric-label">Species below threshold (&lt;{threshold} records)</div>
    </div>""", unsafe_allow_html=True)

with c3:
    pct = round(100 * len(gap_df) / len(filtered), 1) if len(filtered) > 0 else 0
    st.markdown(f"""
    <div class="metric-card teal">
        <div class="metric-value">{pct}%</div>
        <div class="metric-label">Percentage with data gaps</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── Figure 1: Top 20 worst data gaps ─────────────────────────────
st.markdown("### Species with Lowest Occurrence Records")
st.caption(f"Top 20 species in current selection with fewest GBIF records (threshold: {threshold})")

top20 = (gap_df.nsmallest(20, 'total_occurrences')
               .sort_values('total_occurrences', ascending=True))

if len(top20) > 0:
    # Truncate long names
    top20 = top20.copy()
    top20['display_name'] = top20['sci_name'].apply(
        lambda x: x[:48] + '…' if len(x) > 48 else x
    )

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=top20['total_occurrences'],
        y=top20['display_name'],
        orientation='h',
        marker_color='#c0392b',
        marker_line_color='#922b21',
        marker_line_width=0.5,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "GBIF records: %{x}<br>"
            "<extra></extra>"
        )
    ))

    fig1.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(family='Arial', size=12),
        height=520,
        margin=dict(l=20, r=80, t=20, b=40),
        xaxis=dict(
            title="GBIF Occurrence Records",
            gridcolor='#eeeeee',
            zeroline=True,
            zerolinecolor='#cccccc'
        ),
        yaxis=dict(
            tickfont=dict(size=10, color='#333'),
            autorange='reversed'
        )
    )

    # Italic species names via ticktext
    fig1.update_yaxes(
        ticktext=[f"<i>{n}</i>" for n in top20['display_name']],
        tickvals=top20['display_name']
    )

    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("No species below the current threshold in this selection.")

# ── Figure 2: Grouped bar — total vs gap by class ─────────────────
st.markdown("### Data Gaps by Taxonomic Class")
st.caption("Total species vs. species below occurrence threshold, grouped by class")

if selected_cat == "All":
    cs_filtered = class_summary.copy()
    chart_title = "All IUCN Categories"
else:
    cs_filtered = class_summary[class_summary['category'] == selected_cat].copy()
    chart_title = f"Category: {selected_cat}"

# Recompute from filtered df for accurate threshold
class_agg = (filtered.groupby('class')
             .agg(
                 total_species=('sci_name', 'count'),
                 gap_species=('total_occurrences', lambda x: (x < threshold).sum())
             )
             .reset_index()
             .sort_values('total_species', ascending=False)
             .head(15))

if len(class_agg) > 0:
    fig2 = go.Figure()

    fig2.add_trace(go.Bar(
        name='Total Species',
        x=class_agg['class'],
        y=class_agg['total_species'],
        marker_color='#1abc9c',
        marker_line_color='white',
        marker_line_width=0.5,
        hovertemplate="<b>%{x}</b><br>Total: %{y:,}<extra></extra>"
    ))

    fig2.add_trace(go.Bar(
        name=f'Species with <{threshold} Records',
        x=class_agg['class'],
        y=class_agg['gap_species'],
        marker_color='#c0392b',
        marker_line_color='white',
        marker_line_width=0.5,
        hovertemplate="<b>%{x}</b><br>Data gaps: %{y:,}<extra></extra>"
    ))

    # Percentage annotations
    annotations = []
    for _, row in class_agg.iterrows():
        if row['total_species'] > 0:
            pct_val = 100 * row['gap_species'] / row['total_species']
            annotations.append(dict(
                x=row['class'],
                y=row['gap_species'] + max(class_agg['total_species']) * 0.015,
                text=f"{pct_val:.0f}%",
                showarrow=False,
                font=dict(size=9, color='#c0392b', family='Arial'),
                xanchor='center'
            ))

    fig2.update_layout(
        barmode='group',
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(family='Arial', size=11),
        height=440,
        margin=dict(l=20, r=20, t=20, b=80),
        xaxis=dict(
            tickangle=-35,
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            title="Number of Species",
            gridcolor='#eeeeee'
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom', y=1.02,
            xanchor='right', x=1,
            font=dict(size=10)
        ),
        annotations=annotations
    )

    st.plotly_chart(fig2, use_container_width=True)

# ── Data table ────────────────────────────────────────────────────
st.markdown("### Full Species Data")
st.caption(f"Showing {len(filtered):,} species — sortable by any column")

display_cols = {
    'sci_name': 'Species',
    'category': 'IUCN',
    'class': 'Class',
    'order_name': 'Order',
    'family': 'Family',
    'total_occurrences': 'GBIF Records',
    'population_trend': 'Trend'
}

table_df = filtered[list(display_cols.keys())].rename(columns=display_cols)
table_df = table_df.sort_values('GBIF Records')

# Highlight gap rows
def highlight_gaps(row):
    if row['GBIF Records'] < threshold:
        return ['background-color: #fdecea'] * len(row)
    return [''] * len(row)

st.dataframe(
    table_df.style.apply(highlight_gaps, axis=1),
    use_container_width=True,
    height=420,
    column_config={
        "Species": st.column_config.TextColumn("Species", width="large"),
        "GBIF Records": st.column_config.NumberColumn("GBIF Records", format="%d"),
    }
)

# Download button
csv_download = filtered.to_csv(index=False).encode('utf-8')
st.download_button(
    label="⬇️ Download filtered data as CSV",
    data=csv_download,
    file_name=f"biodiversity_gaps_{selected_cat}_{selected_class}.csv".replace(" ","_"),
    mime="text/csv"
)

# ── Footer ────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<footer>Data sources: IUCN Red List, GBIF &nbsp;|&nbsp; "
    "Database: bio_database_v2.db (26M records) &nbsp;|&nbsp; "
    "Methodology: LEFT JOIN of iucn_species against aggregated gbif_species occurrence counts &nbsp;|&nbsp; "
    "Built by Neal Doran, Ph.D.</footer>",
    unsafe_allow_html=True
)
