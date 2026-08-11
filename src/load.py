import duckdb
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GenomicDataLoader:
    """Handles loading structured genomic data into a DuckDB database."""

    def __init__(self, db_path: str = "data/processed/genomic_data.duckdb"):
        self.db_path = db_path

    def load_data(self, df: pd.DataFrame, table_name: str = "variants"):
        """Loads a Pandas DataFrame into a DuckDB table.
        Deletes any existing rows for the same gene first, so re-running
        the pipeline (e.g. the daily GitHub Action) never creates duplicates.
        """
        logging.info(f"Loading {len(df)} rows into DuckDB table '{table_name}'...")

        with duckdb.connect(self.db_path) as con:
            # Explicit schema -- matches dashboard.py exactly, so CI-created
            # DBs and locally-created DBs never drift into different column types
            con.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    gene_symbol VARCHAR,
                    variant_id VARCHAR,
                    chromosome VARCHAR,
                    start_position INTEGER,
                    end_position INTEGER,
                    consequence VARCHAR,
                    clinical_significance VARCHAR
                )
            """)

            gene_symbol = df['gene_symbol'].iloc[0]
            con.execute(f"DELETE FROM {table_name} WHERE gene_symbol = ?", [gene_symbol])
            logging.info(f"Cleared old rows for gene '{gene_symbol}' before reloading.")

            con.execute(f"INSERT INTO {table_name} SELECT * FROM df")

            logging.info(f"Successfully loaded data into '{self.db_path}'.")

# --- Test the Full Pipeline (E --> T --> L) ---
if __name__ == "__main__":
    from extract import GenomicDataExtractor
    from transform import GenomicDataTransformer

    extractor = GenomicDataExtractor()
    raw_data = extractor.fetch_variants_for_gene("HBB")

    transformer = GenomicDataTransformer()
    clean_df = transformer.clean_variants(raw_data, "HBB")

    loader = GenomicDataLoader()
    loader.load_data(clean_df)

    logging.info("Verifying database contents...")
    with duckdb.connect("data/processed/genomic_data.duckdb") as con:
        result = con.execute("SELECT COUNT(*) FROM variants").fetchone()
        logging.info(f"Database currently holds {result[0]} rows in the 'variants' table.")
        