import requests
import json
import time
import logging
from typing import List, Dict

# Set up logging so we can track the pipeline's progress in the terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GenomicDataExtractor:
    """Handles autonomous extraction of genomic data from the Ensembl REST API."""

    def __init__(self):
        self.base_url = "https://rest.ensembl.org"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Abdul_Raffay_Genomic_Pipeline/1.0"
        }

    def fetch_variants_for_gene(self, identifier: str, species: str = "homo_sapiens") -> List[Dict]:
        """
        Step 1: Smart-detect if input is an Ensembl ID, Accession Number, or Gene Symbol.
        Step 2: Fetch known variants for that ID with a 3-attempt retry system.
        """
        identifier = identifier.strip().upper()
        gene_id = None
        
        logging.info(f"Processing input: {identifier} under species: {species}")

        # Step 1: Auto-Detect Input Type & Get Ensembl ID
        if identifier.startswith("ENS"):
            # Catches Ensembl IDs across species (e.g., ENSG for human, ENSCHIG for goat)
            gene_id = identifier
            logging.info(f"Direct Ensembl ID detected: {gene_id}")
            
        elif identifier.startswith(("NM_", "NP_", "NG_", "NC_", "LRG_")):
            # Accession number routing with retries
            logging.info("Accession number detected. Querying cross-references...")
            
            # Updated to /xrefs/symbol/ to return Ensembl Objects directly
            xref_url = f"{self.base_url}/xrefs/symbol/{species}/{identifier}"
            response = None
            
            for attempt in range(3):
                response = requests.get(xref_url, headers=self.headers)
                if response.status_code == 200:
                    break
                logging.warning(f"Attempt {attempt+1}/3 failed for {identifier} ({response.status_code}), retrying...")
                time.sleep(3)
                
            if response and response.status_code == 200 and response.json():
                xref_data = response.json()
                
                # Pass 1: Hunt specifically for the Ensembl 'gene' ID
                for item in xref_data:
                    if 'id' in item and str(item['id']).startswith('ENS') and item.get('type') == 'gene':
                        gene_id = item['id']
                        break 
                
                # Pass 2 (Fallback): If no gene was found, grab any valid Ensembl ID
                if not gene_id:
                    for item in xref_data:
                        if 'id' in item and str(item['id']).startswith('ENS'):
                            gene_id = item['id']
                            break

                if gene_id:
                    logging.info(f"Successfully mapped Accession {identifier} to Ensembl ID: {gene_id}")
                else:
                    logging.error(f"Accession {identifier} mapped successfully, but Ensembl returned no valid ENS IDs.")
                    return []
            else:
                logging.error(f"Failed to map Accession {identifier}. API returned {response.status_code if response else 'None'}")
                return []
                
        else:
            # Standard gene symbol routing with retries
            logging.info("Standard gene symbol detected. Looking up Ensembl ID...")
            lookup_url = f"{self.base_url}/lookup/symbol/{species}/{identifier}?expand=1"
            response = None
            
            for attempt in range(3):
                response = requests.get(lookup_url, headers=self.headers)
                if response.status_code == 200:
                    break
                logging.warning(f"Attempt {attempt+1}/3 failed for {identifier} ({response.status_code}), retrying...")
                time.sleep(3)

            if response and response.status_code == 200:
                gene_data = response.json()
                gene_id = gene_data.get('id')
            else:
                logging.error(f"Failed to find gene {identifier} after 3 attempts. API returned {response.status_code if response else 'None'}")
                return []

        if not gene_id:
            logging.error(f"No valid Ensembl ID could be resolved for {identifier}.")
            return []

        # Step 2: Fetch Variants associated with this Gene
        logging.info(f"Fetching variants for Ensembl ID: {gene_id}...")
        overlap_url = f"{self.base_url}/overlap/id/{gene_id}?feature=variation"
        var_response = None
        
        for attempt in range(3):
            var_response = requests.get(overlap_url, headers=self.headers)
            if var_response.status_code == 200:
                break
            logging.warning(f"Attempt {attempt+1}/3 failed for {gene_id} ({var_response.status_code}), retrying...")
            time.sleep(3)

        if var_response and var_response.status_code != 200:
            logging.error(f"Failed to fetch variants for {gene_id} after 3 attempts. API returned {var_response.status_code}")
            return []

        variants = var_response.json()
        logging.info(f"Successfully extracted {len(variants)} variants for {identifier}.")
        return variants


# --- Test the Extractor ---
if __name__ == "__main__":
    extractor = GenomicDataExtractor()

    # 1. Test Goat Gene using a direct Ensembl Goat ID (Bypasses the symbol lookup limits)
    print("\n--- Testing Goat Gene (Direct ID) ---")
    goat_variants = extractor.fetch_variants_for_gene("ENSCHIG00000013327", species="capra_hircus")
    if goat_variants:
        print(f"Successfully retrieved {len(goat_variants)} variants for the goat gene.")

    # 2. Test Mouse NCBI Accession Number (Hunting loop will now successfully find Trp53)
    print("\n--- Testing Mouse Accession Number ---")
    accession_variants = extractor.fetch_variants_for_gene("NM_011640", species="mus_musculus")
    if accession_variants:
        print(f"Successfully retrieved {len(accession_variants)} variants for Accession NM_011640.")