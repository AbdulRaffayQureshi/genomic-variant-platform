import duckdb
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GenomicDataLoader:
    """Handles loading structured gnomic data into a DuckDB database."""

    def __init__(self, db_path: str = "data/processed/genomic_data.duckdb"):
        # This is where our Database file will be stored
        self.db_path = db_path
    
    def load_data(self, df: pd.DataFrame, table_name: str = "variants"):
        """Loads a Pandas DataFrame into a DuckDB table."""
        logging.info(f"Loading {len(df)} rows into DuckDB table '{table_name}'...")

        # Connect to the DuckDB database (it automatically creates the file if it doesn't exist)
        with duckdb.connect(self.db_path) as con:
            # First, we create the table schema if this is the very first time we are running it
            con.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df LIMIT 0")
            
            # Then, we insert our clean Pandas DataFrame directly into the database
            con.execute(f"INSERT INTO {table_name} SELECT * FROM df")
            
            logging.info(f"Successfully loaded data into '{self.db_path}'.")

# --- Test the Full Pipeline (E --> T --> L) ---
if __name__ == "__main__":
    from extract import GenomicDataExtractor
    from transform import GenomicDataTransformer

    # 1. Extract the raw data (Phase 1)
    extractor = GenomicDataExtractor()
    raw_data = extractor.fetch_variants_for_gene("HBB")

    # 2. Transform the data (Phase 2)
    transformer = GenomicDataTransformer()
    clean_df = transformer.clean_variants(raw_data)

    # 3. Load the data into DuckDB (Phase 3)
    loader = GenomicDataLoader()
    loader.load_data(clean_df)

    # ---Verify its working---
    logging.info("Verifying database contents...")
    with duckdb.connect("data/processed/genomic_data.duckdb") as con:
        # We query the database using standard SQL to count the rows
        result = con.execute("SELECT COUNT(*) FROM variants").fetchone()
        logging.info(f"Database currently holds {result[0]} rows in the 'variants' table.")

