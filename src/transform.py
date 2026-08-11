import pandas as pd
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GenomicDataTransformer:
    """Handles the cleaning and structuring of raw genomic JSON data."""

    def clean_variants(self, raw_variants: List[Dict], gene_symbol: str) -> pd.DataFrame:
        """
        Takes raw JSON data from Ensembl and flattens it into a Pandas DataFrame.
        """
        logging.info(f"Transforming{len(raw_variants)} raw variants into a structured table...")

        # Creating an empty list to hold our cleaned rows
        cleaned_data = []

        for variant in raw_variants:
            # We only extract the exact data points we need for our database
            # Using .get() prevents the script from crashing if a field is missing
            clean_row = {
                "gene_symbol": gene_symbol,
                "variant_id": variant.get("id"),
                "chromosome": variant.get("seq_region_name"),
                "start_position": variant.get("start"),
                "end_position": variant.get("end"),
                "consequence": variant.get("consequence_type"),
                # clinical_significance is usually a list, so we join it into a single string (e.g., "pathogenic, risk_factor")
                "clinical_significance": ", ".join(variant.get("clinical_significance", []))
            }
            cleaned_data.append(clean_row)

        # Convert the list of cleaned Dictionaries into a Pandas DataFrame
        df = pd.DataFrame(cleaned_data)

        logging.info("Transformation complete.")
        return df

# --- Test the Transformer ---
if __name__ == "__main__":
    # To test this, we have to import our Phase 1 extractor!
    from extract import GenomicDataExtractor

    extractor = GenomicDataExtractor()
    transformer = GenomicDataTransformer()

    # 1. Extract the raw data (Phase 1)
    raw_data = extractor .fetch_variants_for_gene("HBB")

    # 2. Transform the data (Phase 2)
    clean_df = transformer.clean_variants(raw_data)

    # 3. Print the first 5 rows of the cleaned DataFrame to verify
    print("\n--- Sample Cleaned Data (Top 5 Rows)---")
    print(clean_df.head())


