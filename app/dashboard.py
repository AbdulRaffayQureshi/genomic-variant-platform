import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import sys
import os

# Add project root directory to path for ETL module access
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.extract import GenomicDataExtractor
from src.transform import GenomicDataTransformer

# 1. Page Configuration & Custom CSS Injection
st.set_page_config(page_title="Genomic Variant Intelligence Platform", layout="wide", page_icon="🧬")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at 15% 10%, rgba(34,211,238,0.10), transparent 40%),
            radial-gradient(circle at 85% 0%, rgba(244,63,94,0.08), transparent 35%),
            #05070a;
    }

    /* Hero */
    .hero-wrap {
        padding: 28px 32px;
        border-radius: 18px;
        background: linear-gradient(135deg, rgba(15,23,42,0.9), rgba(5,7,10,0.9));
        border: 1px solid rgba(148,163,184,0.15);
        box-shadow: 0 0 40px rgba(34,211,238,0.06);
        margin-bottom: 6px;
    }
    .hero-title {
        font-size: 2.9rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #22d3ee, #67e8f9 40%, #f43f5e 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-top: 6px;
        margin-bottom: 14px;
    }
    .badge-row { display: flex; gap: 10px; flex-wrap: wrap; }
    .badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #22d3ee;
        background: rgba(34,211,238,0.08);
        border: 1px solid rgba(34,211,238,0.3);
        padding: 5px 12px;
        border-radius: 999px;
    }
    .badge.red { color: #fb7185; background: rgba(244,63,94,0.08); border-color: rgba(244,63,94,0.3); }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(160deg, rgba(30,41,59,0.6), rgba(15,23,42,0.6));
        border: 1px solid rgba(148,163,184,0.15);
        border-radius: 14px;
        padding: 18px 20px;
        transition: all 0.25s ease;
    }
    div[data-testid="stMetric"]:hover {
        border-color: rgba(34,211,238,0.5);
        box-shadow: 0 0 24px rgba(34,211,238,0.15);
        transform: translateY(-3px);
    }
    div[data-testid="stMetric"] label { color: #64748b !important; font-weight: 600; }
    div[data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 20px; border-bottom: 1px solid rgba(148,163,184,0.15); }
    .stTabs [data-baseweb="tab"] {
        height: 46px; background: transparent; color: #64748b; font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #22d3ee !important;
        border-bottom: 2px solid #22d3ee;
    }

    h1, h2, h3, h4 { color: #f1f5f9; font-weight: 600; }

    /* Selectbox / text input labels */
    label { color: #cbd5e1 !important; font-weight: 600 !important; }

    section[data-testid="stFileUploadDropzone"], div[data-baseweb="select"] > div {
        background-color: rgba(15,23,42,0.7) !important;
        border-color: rgba(148,163,184,0.25) !important;
        border-radius: 10px !important;
    }

    div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; border: 1px solid rgba(148,163,184,0.15); }

    button[kind="secondary"], .stDownloadButton button {
        background: linear-gradient(90deg, #0e7490, #22d3ee) !important;
        color: #05070a !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        transition: box-shadow 0.2s ease;
    }
    .stDownloadButton button:hover { box-shadow: 0 0 20px rgba(34,211,238,0.4); }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-wrap">
    <div class="hero-title">🧬 Genomic Variant Intelligence</div>
    <div class="hero-subtitle">Live ETL pipeline · Ensembl REST API → DuckDB → interactive analytics, across human, mouse, chicken &amp; goat genomes.</div>
    <div class="badge-row">
        <span class="badge">⚡ On-demand extraction</span>
        <span class="badge">🧪 Multi-species support</span>
        <span class="badge red">🚨 Clinical significance flags</span>
        <span class="badge">🗄️ DuckDB-backed cache</span>
    </div>
</div>
""", unsafe_allow_html=True)
st.write("")

# 2. Database Connection
DB_PATH = "data/processed/genomic_data.duckdb"

@st.cache_resource
def get_db_connection():
    os.makedirs("data/processed", exist_ok=True)
    con = duckdb.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS variants (
            gene_symbol VARCHAR,
            variant_id VARCHAR,
            chromosome VARCHAR,
            start_position INTEGER,
            end_position INTEGER,
            consequence VARCHAR,
            clinical_significance VARCHAR
        )
    """)
    return con

con = get_db_connection()

try:
    available_genes = con.execute("SELECT DISTINCT gene_symbol FROM variants").fetchdf()['gene_symbol'].tolist()
    available_genes.sort()
except Exception:
    available_genes = []

# 3. Species Mapping Dictionary
SPECIES_MAP = {
    "Human (Homo sapiens)": "homo_sapiens",
    "Chicken (Gallus gallus)": "gallus_gallus",
    "Goat (Capra hircus)": "capra_hircus",
    "Mouse (Mus musculus)": "mus_musculus"
}

# 4. The "Smart Dropdown" UI (Now with Species Selection)
st.subheader("⚙️ Control Panel")

col_species, col_gene = st.columns(2)

with col_species:
    selected_species_label = st.selectbox("1. Select Target Species:", list(SPECIES_MAP.keys()))
    target_species = SPECIES_MAP[selected_species_label]

with col_gene:
    options = ["-- Select a Gene --"] + available_genes + ["+ Fetch New Gene / Accession..."]
    choice = st.selectbox("2. Choose a gene or fetch a new one:", options)

active_gene = None

if choice == "+ Fetch New Gene / Accession...":
    fetch_input = st.text_input("Enter HGNC Symbol, Ensembl ID, or Accession (e.g., TP53, NM_000546):").strip().upper()
    if fetch_input:
        active_gene = fetch_input
elif choice != "-- Select a Gene --":
    active_gene = choice

# 5. Pipeline Execution & Data Retrieval
if active_gene:
    record_count = con.execute("SELECT COUNT(*) FROM variants WHERE gene_symbol = ?", [active_gene]).fetchone()[0]

    if record_count == 0:
        with st.spinner(f"Querying Ensembl REST API for '{active_gene}' under {target_species}..."):
            try:
                extractor = GenomicDataExtractor()
                raw_data = extractor.fetch_variants_for_gene(active_gene, species=target_species)

                if raw_data:
                    transformer = GenomicDataTransformer()
                    clean_df = transformer.clean_variants(raw_data, active_gene)

                    if not clean_df.empty:
                        con.execute("INSERT INTO variants SELECT * FROM clean_df")
                        st.success(f"Successfully processed and stored {len(clean_df)} variants for '{active_gene}'.")
                        st.cache_resource.clear()
                    else:
                        st.warning(f"Extracted variant dataset was empty for '{active_gene}'.")
                else:
                    st.error(f"Ensembl API returned no variation records for '{active_gene}' in {target_species}. Double check the gene exists under this species.")
            except Exception as e:
                st.error(f"Pipeline error during live data ingestion: {e}")

    df_gene = con.execute("SELECT * FROM variants WHERE gene_symbol = ?", [active_gene]).fetchdf()

    # 6. Dashboard Metrics & Visualizations
    if not df_gene.empty:
        st.divider()
        st.subheader(f"Genomic Profile: `{active_gene}`")

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Variants Mapped", f"{len(df_gene):,}")

        chrom_val = df_gene['chromosome'].iloc[0] if 'chromosome' in df_gene.columns and not df_gene['chromosome'].empty else "N/A"
        m2.metric("Chromosome", str(chrom_val))

        pathogenic_count = len(df_gene[df_gene['clinical_significance'].str.contains('pathogenic', na=False, case=False)]) if 'clinical_significance' in df_gene.columns else 0
        m3.metric("Pathogenic Flags", f"{pathogenic_count:,}")

        tab1, tab2 = st.tabs(["📊 Analytics & Distribution", "📂 Raw Variant Explorer"])

        with tab1:
            c1, c2 = st.columns(2)

            with c1:
                st.markdown("#### Variant Consequence Distribution")
                if 'consequence' in df_gene.columns and not df_gene['consequence'].empty:
                    consequence_counts = df_gene['consequence'].value_counts().reset_index()
                    consequence_counts.columns = ['Consequence Type', 'Count']
                    fig_bar = px.bar(
                        consequence_counts,
                        x='Count',
                        y='Consequence Type',
                        orientation='h',
                        color='Count',
                        color_continuous_scale=[[0, "#0e7490"], [0.5, "#22d3ee"], [1, "#f43f5e"]]
                    )
                    fig_bar.update_layout(
                        margin=dict(l=0, r=0, t=20, b=0),
                        height=350,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#cbd5e1"
                    )
                    st.plotly_chart(fig_bar, width="stretch")

            with c2:
                st.markdown("#### Positional Mutation Mapping")
                if 'start_position' in df_gene.columns and 'consequence' in df_gene.columns:
                    fig_scatter = px.scatter(
                        df_gene,
                        x='start_position',
                        y='consequence',
                        color='consequence',
                        hover_data=['variant_id'] if 'variant_id' in df_gene.columns else None,
                        color_discrete_sequence=px.colors.qualitative.Prism
                    )
                    fig_scatter.update_layout(
                        showlegend=False,
                        margin=dict(l=0, r=0, t=20, b=0),
                        height=350,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#cbd5e1"
                    )
                    st.plotly_chart(fig_scatter, width="stretch")

            st.divider()
            st.markdown("#### Clinical Significance Breakdown")
            if 'clinical_significance' in df_gene.columns:
                clin_sig_data = df_gene['clinical_significance'].replace('', 'Unspecified').fillna('Unspecified')
                clin_sig_counts = clin_sig_data.value_counts().reset_index()
                clin_sig_counts.columns = ['Significance', 'Count']

                fig_donut = px.pie(
                    clin_sig_counts,
                    values='Count',
                    names='Significance',
                    hole=0.6,
                    color_discrete_sequence=["#22d3ee", "#f43f5e", "#67e8f9", "#fb7185", "#0e7490", "#94a3b8"]
                )
                fig_donut.update_layout(
                    margin=dict(l=0, r=0, t=20, b=0),
                    height=350,
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#cbd5e1",
                    legend=dict(font=dict(color="#cbd5e1"))
                )
                st.plotly_chart(fig_donut, width="stretch")

        with tab2:
            st.markdown(f"#### Complete Database Records for `{active_gene}`")
            st.dataframe(df_gene, height=400, width="stretch")

            csv_data = df_gene.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"⬇️ Export `{active_gene}` Data (CSV)",
                data=csv_data,
                file_name=f"{active_gene}_variants.csv",
                mime='text/csv'
            )
else:
    st.info("💡 Select a species and gene above to begin exploring, or fetch a new one from Ensembl.")