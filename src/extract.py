import requests
import json
import logging
from typing import List, Dict

# Set up logging so we can track the pipline's progress in the terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GenomicDataExtractor:
    """Handles autonoumous extraction of genomic data from the Ensembl REST API."""

    def __init__(self):
        self.base_url = "https://rest.ensembl.org"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Abdul_Raffay_Genomic_Pipeline/1.0"
        }

    def fetch_variants_for_gene(self, gene_name: str) -> List[Dict]:
        """
        Step 1: Convert a human-readable gene name (like 'BRCA1') into an Ensembl ID.
        Step 2: Fetch known variants (mutations) for that gene.
        """
        logging.info(f"Looking up Ensembl ID for gene: {gene_name}")

        # Step 1: Look up the Gene ID ---
        lookup_url = f"{self.base_url}/lookup/symbol/homo_sapiens/{gene_name}?expand=1"
        response = requests.get(lookup_url, headers=self.headers)

        if response.status_code != 200:
            logging.error(f"Failed to find gene {gene_name}. API returned {response.status_code}")
            return []

        gene_data = response.json()
        gene_id = gene_data.get('id')
        logging.info(f"Found Ensembl ID: {gene_id}")

        # --- Step 2: Fetch Variants associated with this Gene ---
        logging.info(f"Fetching variants for: {gene_id}...")
        overlap_url = f"{self.base_url}/overlap/id/{gene_id}?feature=variation"
        var_response = requests.get(overlap_url, headers=self.headers)

        if var_response.status_code != 200:
            logging.error(f"Failed to fetch variants. API returned {var_response.status_code}")
            logging.error(f"Ensembl API Error Details: {var_response.text}")
            return []

        variants = var_response.json()
        logging.info(f"Successfully extracted {len(variants)} variants for {gene_name}.")
        return variants

# --- Test the Extractor ---
if __name__ == "__main__":
    extractor = GenomicDataExtractor()

    # We will test this with BRCA1 (a gene heavily associated with breast cancer)
    hbb_variants = extractor.fetch_variants_for_gene("HBB")

    # Print the first variant to see the raw data structure
    if hbb_variants:
        print("\n--- Sample Raw Data Extracted ---")
        print(json.dumps(hbb_variants[0], indent=2))
