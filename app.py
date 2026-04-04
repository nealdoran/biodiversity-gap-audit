"""
Global Biodiversity Data Gap Audit — with RAG Query Layer
Built by Neal Doran, Ph.D. | Bio Database v2
Run: streamlit run app_rag.py
Requires: .streamlit/secrets.toml containing: ANTHROPIC_API_KEY = 'your_key_here'
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os, requests
import anthropic

st.set_page_config(page_title="Biodiversity Data Gap Audit", page_icon="🌿",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
    html, body, [class*="css"] { font-family: Arial, sans-serif; }
    .metric-card { background:#f8f9fa; border-left:4px solid #c0392b;
                   padding:16px 20px; border-radius:4px; margin-bottom:8px; }
    .metric-value { font-size:2.2rem; font-weight:bold; color:#c0392b; }
    .metric-label { font-size:0.85rem; color:#666; margin-top:2px; }
    .metric-card.teal { border-left-color:#1abc9c; }
    .metric-card.teal .metric-value { color:#1abc9c; }
    .metric-card.blue { border-left-color:#1F4E79; }
    .metric-card.blue .metric-value { color:#1F4E79; }
    .rag-answer { background:#fff; border:1px solid #dee2e6; border-radius:4px;
                  padding:16px; margin-top:12px; font-size:1.05rem; line-height:1.6; }
    footer { color:#999; font-size:0.78rem; }
</style>""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def load_data():
    df = pd.read_csv(os.path.join(BASE_DIR, "cr_audit_data.csv"))
    cs = pd.read_csv(os.path.join(BASE_DIR, "class_summary.csv"))
    for col in ['class','order_name','family','population_trend']:
        df[col] = df[col].fillna('Unknown')
    return df, cs

df, class_summary = load_data()

# ── Header ────────────────────────────────────────────────────────
st.markdown("## 🌿 Global Biodiversity Data Gap Audit")
st.markdown("**Cross-audit of IUCN Red List × GBIF Occurrence Data &nbsp;|&nbsp; 26 Million Records**")
st.caption("Built by Neal Doran, Ph.D. &nbsp;|&nbsp; Bio Database v2")
st.divider()

# ── Sidebar ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filters")
    cat_options   = ["All"] + sorted(df['category'].unique().tolist(),
                     key=lambda x: ['CR','EN','VU','NT'].index(x) if x in ['CR','EN','VU','NT'] else 99)
    selected_cat   = st.selectbox("IUCN Category", cat_options)
    class_options  = ["All"] + sorted(df['class'].unique().tolist())
    selected_class = st.selectbox("Taxonomic Class", class_options)
    threshold      = st.slider("Data gap threshold", 0, 100, 10)
    st.divider()
    st.markdown("🔴 **CR** — Critically Endangered")
    st.markdown("🟠 **EN** — Endangered")
    st.markdown("🟡 **VU** — Vulnerable")
    st.markdown("🔵 **NT** — Near Threatened")

# ── Filter ────────────────────────────────────────────────────────
filtered = df.copy()
if selected_cat   != "All": filtered = filtered[filtered['category'] == selected_cat]
if selected_class != "All": filtered = filtered[filtered['class']    == selected_class]
gap_df = filtered[filtered['total_occurrences'] < threshold]

# ── Metrics ───────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="metric-card blue"><div class="metric-value">{len(filtered):,}</div>'
                f'<div class="metric-label">Species in selection</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-value">{len(gap_df):,}</div>'
                f'<div class="metric-label">Below threshold (&lt;{threshold} records)</div></div>', unsafe_allow_html=True)
with c3:
    pct = round(100*len(gap_df)/len(filtered),1) if len(filtered) else 0
    st.markdown(f'<div class="metric-card teal"><div class="metric-value">{pct}%</div>'
                f'<div class="metric-label">Percentage with data gaps</div></div>', unsafe_allow_html=True)
st.divider()

# ── Figure 1 ──────────────────────────────────────────────────────
st.markdown("### Species with Lowest Occurrence Records")
top20 = gap_df.nsmallest(20,'total_occurrences').sort_values('total_occurrences').copy()
if len(top20):
    top20['dn'] = top20['sci_name'].apply(lambda x: x[:48]+'…' if len(x)>48 else x)
    fig1 = go.Figure(go.Bar(x=top20['total_occurrences'], y=top20['dn'],
                            orientation='h', marker_color='#c0392b',
                            hovertemplate="<b>%{y}</b><br>Records: %{x}<extra></extra>"))
    fig1.update_layout(paper_bgcolor='white', plot_bgcolor='white',
                       font=dict(family='Arial',size=12), height=520,
                       margin=dict(l=20,r=80,t=20,b=40),
                       xaxis=dict(title="GBIF Occurrence Records", gridcolor='#eee'),
                       yaxis=dict(autorange='reversed',
                                  ticktext=[f"<i>{n}</i>" for n in top20['dn']],
                                  tickvals=top20['dn']))
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("No species below threshold in current selection.")

# ── Figure 2 ──────────────────────────────────────────────────────
st.markdown("### Data Gaps by Taxonomic Class")
ca = (filtered.groupby('class')
      .agg(total=('sci_name','count'), gaps=('total_occurrences', lambda x:(x<threshold).sum()))
      .reset_index().sort_values('total',ascending=False).head(15))
if len(ca):
    annots = [dict(x=r['class'], y=r['gaps']+max(ca['total'])*0.015,
                   text=f"{100*r['gaps']/r['total']:.0f}%", showarrow=False,
                   font=dict(size=9,color='#c0392b',family='Arial'), xanchor='center')
              for _,r in ca.iterrows() if r['total']>0]
    fig2 = go.Figure([
        go.Bar(name='Total Species', x=ca['class'], y=ca['total'],
               marker_color='#1abc9c', hovertemplate="<b>%{x}</b><br>Total: %{y:,}<extra></extra>"),
        go.Bar(name=f'<{threshold} Records', x=ca['class'], y=ca['gaps'],
               marker_color='#c0392b', hovertemplate="<b>%{x}</b><br>Gaps: %{y:,}<extra></extra>")
    ])
    fig2.update_layout(barmode='group', paper_bgcolor='white', plot_bgcolor='white',
                       font=dict(family='Arial',size=11), height=440,
                       margin=dict(l=20,r=20,t=20,b=80),
                       xaxis=dict(tickangle=-35), yaxis=dict(title="Species Count",gridcolor='#eee'),
                       legend=dict(orientation='h',yanchor='bottom',y=1.02,xanchor='right',x=1),
                       annotations=annots)
    st.plotly_chart(fig2, use_container_width=True)

# ── Data Table ────────────────────────────────────────────────────
st.markdown("### Full Species Data")
dcols = {'sci_name':'Species','category':'IUCN','class':'Class','order_name':'Order',
         'family':'Family','total_occurrences':'GBIF Records','population_trend':'Trend'}
tdf = filtered[list(dcols.keys())].rename(columns=dcols).sort_values('GBIF Records')
def hi(r): return ['background-color:#fdecea']*len(r) if r['GBIF Records']<threshold else ['']*len(r)
st.dataframe(tdf.style.apply(hi,axis=1), use_container_width=True, height=420,
             column_config={"Species":st.column_config.TextColumn("Species",width="large"),
                            "GBIF Records":st.column_config.NumberColumn(format="%d")})
st.download_button("⬇️ Download filtered data as CSV",
                   filtered.to_csv(index=False).encode('utf-8'),
                   file_name=f"biodiversity_gaps_{selected_cat}_{selected_class}.csv".replace(" ","_"),
                   mime="text/csv")

# ═══════════════════════════════════════════════════════════════
# RAG QUERY LAYER
# ═══════════════════════════════════════════════════════════════
st.divider()
st.markdown("## 🤖 Ask the Database")
st.markdown("Ask a natural language question about the biodiversity data. "
            "Gemini converts it to a query and returns a plain-English answer.")

if 'query_count' not in st.session_state:
    st.session_state.query_count = 0
MAX_Q = 20

# Example question buttons using session state
if 'question_text' not in st.session_state:
    st.session_state.question_text = ""

st.markdown("**Try an example — click to load into box:**")
examples = [
    "Which critically endangered amphibians have zero occurrence records?",
    "What percentage of critically endangered mammals are data-deficient?",
    "List the top 10 most data-deficient reptile species",
    "How many critically endangered species are freshwater versus terrestrial?",
]
ec1, ec2 = st.columns(2)
for i, ex in enumerate(examples):
    if (ec1 if i%2==0 else ec2).button(f"💬 {ex}", key=f"ex{i}"):
        st.session_state.question_text = ex
        st.rerun()

question = st.text_input("Your question:",
                         value=st.session_state.question_text,
                         placeholder="e.g. Which fish have the fewest occurrence records?")
st.session_state.question_text = question

st.markdown("---")
answer_area = st.empty()

if st.button("🔍 Ask", type="primary") and question.strip():
    if st.session_state.query_count >= MAX_Q:
        st.warning(f"Session limit of {MAX_Q} queries reached. Refresh to reset.")
    else:
        try:
            api_key = st.secrets["ANTHROPIC_API_KEY"]
        except Exception:
            st.error("Add ANTHROPIC_API_KEY to .streamlit/secrets.toml")
            st.stop()

           col_info = """
DataFrame 'df' columns:
- sci_name (str): scientific name (e.g. 'Panthera tigris')
- category (str): IUCN Red List category. Values are ONLY: 'CR' (Critically Endangered), 'EN' (Endangered), 'VU' (Vulnerable), 'NT' (Near Threatened). NOTE: This dataset does NOT contain 'DD' (Data Deficient) or 'LC' (Least Concern) species. If asked about data-deficient species, explain that IUCN Data Deficient (DD) species are not included in this dataset, which only covers CR/EN/VU/NT species.
- class (str): taxonomic class. Common values: 'Mammalia', 'Amphibia', 'Actinopterygii', 'Reptilia', 'Aves', 'Gastropoda', 'Insecta', etc.
- order_name (str): taxonomic order
- family (str): taxonomic family
- genus (str): taxonomic genus
- population_trend (str): 'Decreasing', 'Stable', 'Increasing', or 'Unknown'
- marine (int): 1 = marine species, 0 = not marine
- freshwater (int): 1 = freshwater species, 0 = not freshwater
- terrestrial (int): 1 = terrestrial species, 0 = not terrestrial
  NOTE: A species can belong to MULTIPLE habitat types (e.g. marine=1 AND freshwater=1).
  To count species by habitat: terrestrial_count = (df['terrestrial']==1).sum(); freshwater_count = (df['freshwater']==1).sum(); marine_count = (df['marine']==1).sum()
  To compare habitats, compute each separately and present side by side.
- total_occurrences (int): number of GBIF occurrence records. 0 means no location data exists.

IMPORTANT RULES:
1. This dataset contains ONLY CR/EN/VU/NT species. There are NO 'DD' (Data Deficient) entries. If asked about DD species, set result = "This dataset covers CR, EN, VU, and NT species only. IUCN Data Deficient (DD) species are not included. Consult the full IUCN Red List for DD species."
2. Before any division, always check that the denominator is not zero. Use: denominator = len(subset); result = round(numerator/denominator*100, 1) if denominator > 0 else "No matching species found."
3. For habitat comparisons (marine vs freshwater vs terrestrial), always query each habitat column separately and combine results.
"""


        p1 = f"""Convert this question to pandas code against DataFrame 'df'.
{col_info}
Return ONLY executable Python. No markdown. No backticks. Assign result to variable 'result'.
Question: {question}"""

        with st.spinner("Querying..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                r1 = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": p1}]
                )
                code = r1.content[0].text.strip().strip('`').replace('python','').strip()
            except Exception as e:
                st.error("Query generation failed. Please try again in a moment.")
                st.stop()

        try:
            lv = {'df': df.copy(), 'pd': pd}
            exec(code, {}, lv)
            result = lv.get('result')
            if result is None: st.warning("No result returned. Try rephrasing."); st.stop()
            if isinstance(result, pd.DataFrame):
                result_df  = result
                result_str = result.head(30).to_string(index=False)
            elif isinstance(result, pd.Series):
                result_df  = result.reset_index()
                result_str = result_df.to_string(index=False)
            else:
                result_df  = None
                result_str = str(result)
        except Exception as e:
            st.error(f"Execution error: {e}")
            st.caption(f"Generated code: `{code}`"); st.stop()

        p2 = f"""Summarize this data result in 2-4 plain English sentences for a general audience.
Be specific — use actual numbers and species names. Do not say 'dataframe' or 'query'.
Question: {question}
Result: {result_str[:2000]}"""

        with st.spinner("Summarizing..."):
            try:
                r2 = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": p2}]
                )
                answer = r2.content[0].text.strip()
            except Exception as e:
                answer = "Summary unavailable. Please try again."

        st.session_state.query_count += 1
        st.markdown(f'<div class="rag-answer">{answer}</div>', unsafe_allow_html=True)
        if result_df is not None and len(result_df):
            with st.expander(f"📊 Raw data ({len(result_df)} rows)"):
                st.dataframe(result_df, use_container_width=True)
        st.caption(f"Queries this session: {st.session_state.query_count}/{MAX_Q}")

# ── Footer ────────────────────────────────────────────────────────
st.divider()
st.markdown("<footer>Data: IUCN Red List, GBIF &nbsp;|&nbsp; 26M records &nbsp;|&nbsp; "
            "AI: Anthropic Claude Haiku &nbsp;|&nbsp; Built by Neal Doran, Ph.D.</footer>",
            unsafe_allow_html=True)
