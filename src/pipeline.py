import logging
import time

# We import the three classes you built in Phases 1, 2, and 3
from extract import GenomicDataExtractor
from transform import GenomicDataTransformer
from load import GenomicDataLoader

# Setup our master logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_pipeline(gene_symbol: str = "HBB"):
    """Executes the full Extract, Transform, Load sequence sequentially."""
    start_time = time.time()
    logging.info(f"🚀 Starting Genomic ETL Pipeline for gene: {gene_symbol}")

    try:
        # Phase 1: Extract
        logging.info(">>> Phase 1: EXTRACT")
        extractor = GenomicDataExtractor()
        raw_data = extractor.fetch_variants_for_gene(gene_symbol)

        # Safety check: if extraction fails, stops the pipeline so we don't load garbage data
        if not raw_data:
            logging.error("Pipeline stopped: No raw data extracted.")
            return

        # Phase 2: Transform
        logging.info(">>> Phase 2: TRANSFORM")
        transformer = GenomicDataTransformer()
        clean_df = transformer.clean_variants(raw_data)

        # Safety check: ensure the dataframe actually has rows
        if clean_df.empty:
            logging.error("Pipeline stopped: Transformed dataset is empty.")
            return
        
        # Phase 3: Load
        logging.info(">>> Phase 3: LOAD")
        loader = GenomicDataLoader()
        loader.load_data(clean_df)
        
        elapsed_time = round(time.time() - start_time, 2)
        logging.info(f"✅ Pipeline completed successfully in {elapsed_time} seconds!")
        
    except Exception as e:
        # If any module crashes, the orchestrator catches the error gracefully
        logging.error(f"❌ Pipeline failed with error: {e}")

if __name__ == "__main__":
    # You can easily change this target gene to track different diseases!
    run_pipeline("HBB")