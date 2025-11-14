#!/bin/bash -l
#SBATCH --job-name=example-ollama
#SBATCH --time=00:30:00
#SBATCH --partition=gpu
#SBATCH --account=p200981
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --qos=default
#SBATCH --output=logs/example-ollama_%j.out
#SBATCH --error=logs/example-ollama_%j.err

echo "Date              = $(date)"
echo "Hostname          = $(hostname -s)"
echo "Working Directory = $(pwd)"

# Load required modules
module add Apptainer

# Pull container if needed
if [ ! -f "ollama_ollama.sif" ]; then
    echo "Pulling container image..."
    apptainer pull docker://ollama/ollama
fi

# Start the service
echo "Starting example-ollama..."
apptainer exec --nv ollama_ollama.sif ollama serve
