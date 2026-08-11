import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px

# 1. Page Configuration (must be the first Streamlit command)
st.set_page_config(page_title="Genomic Variant Platform", layout="wide")

st.title("🧬 Genomic Variant Intelligence Platform")
st.markdown("Interactive dashboard for exploring annotated genetic mutations.")

# 2. Data Loading Engine
# The @st.cache_data decorator is crucial. It tells Streamlit to cache the database 
# query so it doesn't re-run the heavy SQL task every time the user clicks a button.
@st.cache_data
def load_db_data():
    # Connect to our DuckDB file and fetch the whole table as a Pandas DataFrame
    with duckdb.connect("data/processed/genomic_data.duckdb") as con:
        df = con.execute("SELECT * FROM variants").fetchdf()
    return df

# Fetch the data
df = load_db_data()

# 3. UI Layout: Top Metrics
st.markdown("### Dataset Overview")
col1, col2, col3 = st.columns(3)
col1.metric("Total Variants", len(df))
col2.metric("Unique Chromosomes", df['chromosome'].nunique())
col3.metric("Pathogenic Variants", len(df[df['clinical_significance'].str.contains('pathogenic', na=False, case=False)]))

# 4. UI Layout: Interactive Charts
st.markdown("### Variant Consequences Breakdown")
# We count how many times each consequence happens (e.g., missense, frameshift)
consequence_counts = df['consequence'].value_counts().reset_index()
consequence_counts.columns = ['Consequence Type', 'Count']

# Use Plotly to make a beautiful, interactive bar chart
fig = px.bar(
    consequence_counts, 
    x='Consequence Type', 
    y='Count', 
    color='Count',
    color_continuous_scale='Viridis'
)
st.plotly_chart(fig, width='stretch')

# 5. UI Layout: Raw Data Explorer
st.markdown("### Variant Explorer")
st.dataframe(df, width='stretch', height=400)