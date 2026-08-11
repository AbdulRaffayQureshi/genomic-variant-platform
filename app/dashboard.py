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
    .stApp {
        background-color: #0e1117;
    }
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        border-color: #38bdf8;
    }
    div[data-testid="metric-container"] > div:nth-child(2) {
        color: #38bdf8 !important; 
        font-weight: 700;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        color: #f8fafc;
        border-bottom: 2px solid #38bdf8;
    }
    h1, h2, h3 {
        color: #f8fafc;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🧬 Genomic Variant Intelligence")
st.markdown("Explore annotated genetic mutations across multiple species genomes.")
st.divider()

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
    "Mouse (Mus musculus)": "mus_musculus",
    "Avian Adenovirus": "avian_adenovirus"
}

# 4. The "Smart Dropdown" UI (Now with Species Selection)
st.subheader("⚙️ Control Panel")

# Create a side-by-side layout for a cleaner UI
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
                # We now pass the user-selected species directly into the backend!
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
                    st.error(f"Ensembl API returned no variation records for '{active_gene}' in {target_species}.")
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
                        color_continuous_scale='Tealgrn'
                    )
                    fig_bar.update_layout(
                        margin=dict(l=0, r=0, t=20, b=0), 
                        height=350,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)"
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
                        hover_data=['variant_id'] if 'variant_id' in df_gene.columns else None
                    )
                    fig_scatter.update_layout(
                        showlegend=False, 
                        margin=dict(l=0, r=0, t=20, b=0), 
                        height=350,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)"
                    )
                    st.plotly_chart(fig_scatter, width="stretch")
            
            st.divider()
            st.markdown("#### Clinical Significance Breakdown")
            if 'clinical_significance' in df_gene.columns:
                # Safely handle missing values without triggering the Pandas regex bool error
                clin_sig_data = df_gene['clinical_significance'].replace('', 'Unspecified').fillna('Unspecified')
                clin_sig_counts = clin_sig_data.value_counts().reset_index()
                clin_sig_counts.columns = ['Significance', 'Count']
                
                fig_donut = px.pie(
                    clin_sig_counts, 
                    values='Count', 
                    names='Significance', 
                    hole=0.5,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_donut.update_layout(
                    margin=dict(l=0, r=0, t=20, b=0), 
                    height=350,
                    paper_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_donut, width="stretch")

        with tab2:
            st.markdown(f"#### Complete Database Records for `{active_gene}`")
            # Width stretch enforced
            st.dataframe(df_gene, height=400, width="stretch")

            csv_data = df_gene.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"⬇️ Export `{active_gene}` Data (CSV)",
                data=csv_data,
                file_name=f"{active_gene}_variants.csv",
                mime='text/csv'
            )