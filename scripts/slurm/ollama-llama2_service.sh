#!/bin/bash -l
#SBATCH --job-name=ollama-llama2
#SBATCH --time=01:00:00
#SBATCH --partition=gpu
#SBATCH --account=p200981
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --qos=default
#SBATCH --output=logs/ollama-llama2_%j.out
#SBATCH --error=logs/ollama-llama2_%j.err

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
echo "Starting ollama-llama2..."
apptainer exec --nv ollama_ollama.sif ollama serve
