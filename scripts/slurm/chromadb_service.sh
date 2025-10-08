#!/bin/bash -l
#SBATCH --job-name=chromadb
#SBATCH --time=00:30:00
#SBATCH --partition=cpu
#SBATCH --account=p200981
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --qos=default
#SBATCH --output=logs/chromadb_%j.out
#SBATCH --error=logs/chromadb_%j.err

echo "Date              = $(date)"
echo "Hostname          = $(hostname -s)"
echo "Working Directory = $(pwd)"

# Load required modules
module add Apptainer

# Pull container if needed
if [ ! -f "chromadb_chroma_latest.sif" ]; then
    echo "Pulling container image..."
    apptainer pull docker://chromadb/chroma:latest
fi

# Start the service
echo "Starting chromadb..."
apptainer exec --nv chromadb_chroma_latest.sif echo 'Service started'
