#!/bin/bash

# 1. Navigate to the project folder
cd /home/arq-ubuntu/genomic-variant-platform

# 2. Activate the uv virtual environment
source .venv/bin/activate

# 3. Run the pipeline and log the output
python3 src/pipeline.py
