#!/bin/bash
# Quick local test script (without SLURM)

set -e

echo "======================================"
echo "AI Factory Benchmarking Framework"
echo "Local Test Run"
echo "======================================"

module add Apptainer
module add Python/3.12.3-GCCcore-13.3.0

# Create necessary directories
mkdir -p logs reports

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Run the benchmark
echo "Starting benchmark..."
python src/main.py --recipe recipe.yml

echo "======================================"
echo "Benchmark completed!"
echo "Check the reports/ directory for results"
echo "======================================"
