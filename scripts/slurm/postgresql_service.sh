#!/bin/bash -l
#SBATCH --job-name=postgresql
#SBATCH --time=00:30:00
#SBATCH --partition=cpu
#SBATCH --account=p200981
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --qos=default
#SBATCH --output=logs/postgresql_%j.out
#SBATCH --error=logs/postgresql_%j.err

echo "Date              = $(date)"
echo "Hostname          = $(hostname -s)"
echo "Working Directory = $(pwd)"

# Load required modules
module add Apptainer

# Pull container if needed
if [ ! -f "postgres_16.sif" ]; then
    echo "Pulling container image..."
    apptainer pull docker://postgres:16
fi

# Start the service
echo "Starting postgresql..."
apptainer exec --nv postgres_16.sif echo 'Service started'
