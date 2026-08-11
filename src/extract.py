import requests
import json
import time
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GenomicDataExtractor:
    """Handles autonomous extraction of genomic data from the Ensembl REST API."""

    def __init__(self):
        self.base_url = "https://rest.ensembl.org"
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Abdul_Raffay_Genomic_Pipeline/1.0"
        }

    def _get_with_retry(self, url: str, label: str, max_attempts: int = 3) -> Optional[requests.Response]:
        response = None
        for attempt in range(max_attempts):
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                return response

            if 400 <= response.status_code < 500 and response.status_code != 429:
                logging.error(f"{label}: permanent error {response.status_code}, not retrying.")
                return response

            logging.warning(f"{label}: attempt {attempt+1}/{max_attempts} failed "
                             f"({response.status_code}), retrying...")
            time.sleep(3)

        return response

    def fetch_variants_for_gene(self, identifier: str, species: str = "homo_sapiens") -> List[Dict]:
        identifier = identifier.strip().upper()
        gene_id = None

        logging.info(f"Processing input: {identifier} under species: {species}")

        if identifier.startswith("ENS"):
            gene_id = identifier
            logging.info(f"Direct Ensembl ID detected: {gene_id}")

        elif identifier.startswith(("NM_", "NP_", "NG_", "NC_", "LRG_")):
            logging.info("Accession number detected. Querying cross-references...")

            xref_url = f"{self.base_url}/xrefs/symbol/{species}/{identifier}"
            response = self._get_with_retry(xref_url, label=f"xref lookup for {identifier}")

            if response is not None and response.status_code == 200 and response.json():
                xref_data = response.json()

                for item in xref_data:
                    if 'id' in item and str(item['id']).startswith('ENS') and item.get('type') == 'gene':
                        gene_id = item['id']
                        break

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
                status = response.status_code if response is not None else 'None'
                logging.error(f"Failed to map Accession {identifier}. API returned {status}")
                return []

        else:
            logging.info("Standard gene symbol detected. Looking up Ensembl ID...")
            lookup_url = f"{self.base_url}/lookup/symbol/{species}/{identifier}?expand=1"
            response = self._get_with_retry(lookup_url, label=f"symbol lookup for {identifier}")

            if response is not None and response.status_code == 200:
                gene_data = response.json()
                gene_id = gene_data.get('id')
            else:
                status = response.status_code if response is not None else 'None'
                logging.error(f"Failed to find gene {identifier}. API returned {status}. "
                               f"Verify the symbol exists under species '{species}'.")
                return []

        if not gene_id:
            logging.error(f"No valid Ensembl ID could be resolved for {identifier}.")
            return []

        logging.info(f"Fetching variants for Ensembl ID: {gene_id}...")
        overlap_url = f"{self.base_url}/overlap/id/{gene_id}?feature=variation"
        var_response = self._get_with_retry(overlap_url, label=f"variant fetch for {gene_id}")

        if var_response is None or var_response.status_code != 200:
            status = var_response.status_code if var_response is not None else 'None'
            logging.error(f"Failed to fetch variants for {gene_id}. API returned {status}")
            return []

        variants = var_response.json()
        logging.info(f"Successfully extracted {len(variants)} variants for {identifier}.")
        return variants


if __name__ == "__main__":
    extractor = GenomicDataExtractor()

    print("\n--- Testing Goat Gene (Direct ID) ---")
    goat_variants = extractor.fetch_variants_for_gene("ENSCHIG00000013327", species="capra_hircus")
    if goat_variants:
        print(f"Successfully retrieved {len(goat_variants)} variants for the goat gene.")

    print("\n--- Testing Mouse Accession Number ---")
    accession_variants = extractor.fetch_variants_for_gene("NM_011640", species="mus_musculus")
    if accession_variants:
        print(f"Successfully retrieved {len(accession_variants)} variants for Accession NM_011640.")

    print("\n--- Testing Mismatched Gene/Species (should fail fast, show 400 not None) ---")
    start = time.time()
    bad_variants = extractor.fetch_variants_for_gene("CSN1S1", species="gallus_gallus")
    elapsed = round(time.time() - start, 1)
    print(f"Finished in {elapsed}s")