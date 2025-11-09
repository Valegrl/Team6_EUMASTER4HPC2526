#!/bin/bash
# Master SLURM script to run the complete benchmark

#SBATCH --job-name=ai_factory_benchmark
#SBATCH --time=02:00:00
#SBATCH --partition=gpu
#SBATCH --account=p200981
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --qos=default
#SBATCH --output=logs/benchmark_%j.out
#SBATCH --error=logs/benchmark_%j.err

echo "======================================"
echo "AI Factory Benchmarking Framework"
echo "======================================"
echo "Date              = $(date)"
echo "Hostname          = $(hostname -s)"
echo "Working Directory = $(pwd)"
echo "Job ID            = $SLURM_JOB_ID"
echo "======================================"

# Load required modules
module purge
module load Apptainer

# module load Python/3.11.3-GCCcore-12.3.0
module load Python/3.12.3-GCCcore-13.3.0 

# Create necessary directories
mkdir -p logs reports

# Install Python dependencies
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

# Run the benchmark
echo "Starting benchmark..."
python src/main.py --recipe recipe.yml

echo "======================================"
echo "Benchmark completed!"
echo "======================================"
