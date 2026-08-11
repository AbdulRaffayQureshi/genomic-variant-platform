import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import sys
import os

# Add your project root to path so we can import your ETL modules directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.extract import GenomicDataExtractor
from src.transform import GenomicDataTransformer

# 1. Page Configuration (must be first Streamlit command)
st.set_page_config(page_title="Genomic Variant Intelligence Platform", layout="wide")

st.title("🧬 Genomic Variant Intelligence Platform")
st.markdown("Type any gene symbol below. If it's not in the database, the platform will fetch and process it on-demand!")

# 2. Database Connection & Table Setup
DB_PATH = "data/processed/genomic_data.duckdb"

def get_connection():
    os.makedirs("data/processed", exist_ok=True)
    return duckdb.connect(DB_PATH)

# Initialize table if it doesn't exist yet
con = get_connection()
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
con.close()

# 3. On-Demand Search Bar
user_gene = st.text_input("🔍 Search or Fetch Gene Symbol:", "").strip().upper()

if user_gene:
    con = get_connection()
    # Check if this gene is already stored locally in our database
    existing_check = con.execute("SELECT COUNT(*) FROM variants WHERE gene_symbol = ?", [user_gene]).fetchone()[0]
    
    if existing_check == 0:
        with st.spinner(f"Gene '{user_gene}' not found locally. Fetching live data from Ensembl API..."):
            try:
                # 1. Extract using your actual extraction method and supporting species argument
                extractor = GenomicDataExtractor()
                
                # Dynamic species handling for human vs viral genes
                target_species = "avian_adenovirus" if user_gene.startswith("FADV") else "homo_sapiens"
                
                raw_data = extractor.fetch_variants_for_gene(user_gene, species=target_species)
                
                if raw_data:
                    # 2. Transform
                    transformer = GenomicDataTransformer()
                    clean_df = transformer.clean_variants(raw_data, user_gene)
                    
                    # 3. Load into DuckDB
                    con.execute("INSERT INTO variants SELECT * FROM clean_df")
                    st.success(f"Successfully fetched and loaded data for {user_gene}!")
                else:
                    st.warning(f"No data returned from Ensembl for gene: {user_gene}")
            except Exception as e:
                st.error(f"Failed to fetch gene data: {e}")
    con.close()

# 4. Load Data for Display
@st.cache_data
def load_db_data(trigger_refresh=0):
    with duckdb.connect(DB_PATH) as con:
        df = con.execute("SELECT * FROM variants").fetchdf()
    return df

df = load_db_data(user_gene if user_gene else 0)

# Filter dataframe based on user search input
if user_gene and not df.empty and 'gene_symbol' in df.columns:
    df_filtered = df[df['gene_symbol'] == user_gene]
else:
    df_filtered = df

# 5. UI Layout: Top Metrics & Visualizations
if not df_filtered.empty:
    current_gene_display = user_gene if user_gene else ", ".join(df['gene_symbol'].unique()) if 'gene_symbol' in df.columns else "All"
    st.markdown(f"### Dataset Overview for: `{current_gene_display}`")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Variants", len(df_filtered))
    col2.metric("Unique Chromosomes", df_filtered['chromosome'].nunique() if 'chromosome' in df_filtered.columns else 0)
    col3.metric("Pathogenic Variants", len(df_filtered[df_filtered['clinical_significance'].str.contains('pathogenic', na=False, case=False)]) if 'clinical_significance' in df_filtered.columns else 0)

    # 6. Interactive Charts
    st.markdown("### Variant Consequences Breakdown")
    if 'consequence' in df_filtered.columns:
        consequence_counts = df_filtered['consequence'].value_counts().reset_index()
        consequence_counts.columns = ['Consequence Type', 'Count']

        fig = px.bar(
            consequence_counts, 
            x='Consequence Type', 
            y='Count', 
            color='Count',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig, width='stretch')

    # 7. Raw Data Explorer
    st.markdown("### Variant Explorer")
    st.dataframe(df_filtered, height=400, width='stretch')
else:
    st.info("Enter a gene symbol above to begin exploring genetic variants.")