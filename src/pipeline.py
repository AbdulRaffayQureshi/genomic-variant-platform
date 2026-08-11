import logging
import time
import sys
import os

# Ensure project root is accessible for module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.extract import GenomicDataExtractor
from src.transform import GenomicDataTransformer
from src.load import GenomicDataLoader

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Default starter pack of critical human genes
STARTER_GENES = ["BRCA1", "TP53", "EGFR", "CFTR", "HBB"]

def run_pipeline(gene_list: list = None):
    """Executes the ETL sequence across a starter pack of genes."""
    if gene_list is None:
        gene_list = STARTER_GENES

    start_time = time.time()
    logging.info(f"🚀 Starting Automated Pipeline for {len(gene_list)} starter genes: {gene_list}")

    extractor = GenomicDataExtractor()
    transformer = GenomicDataTransformer()
    loader = GenomicDataLoader()

    successful_loads = 0

    for gene_symbol in gene_list:
        logging.info(f"\n--- Processing Gene: {gene_symbol} ---")
        try:
            # Determine species context (handling viral vs human gene lookups)
            target_species = "avian_adenovirus" if gene_symbol.startswith("FADV") else "homo_sapiens"

            # Phase 1: Extract
            raw_data = extractor.fetch_variants_for_gene(gene_symbol, species=target_species)
            if not raw_data:
                logging.warning(f"Skipping {gene_symbol}: No raw data retrieved.")
                continue

            # Phase 2: Transform
            clean_df = transformer.clean_variants(raw_data, gene_symbol)
            if clean_df.empty:
                logging.warning(f"Skipping {gene_symbol}: Transformed dataset is empty.")
                continue

            # Phase 3: Load
            loader.load_data(clean_df, "variants")
            successful_loads += 1
            logging.info(f"✅ Successfully loaded {gene_symbol} into DuckDB.")

        except Exception as e:
            logging.error(f"❌ Error processing {gene_symbol}: {e}")
        
        time.sleep(2)  # be polite to Ensembl's server, avoid rate-limit/500s

    elapsed_time = round(time.time() - start_time, 2)
    logging.info(f"\n🎉 Starter Pack Pipeline completed! Loaded {successful_loads}/{len(gene_list)} genes in {elapsed_time}s.")

if __name__ == "__main__":
    run_pipeline()