#!/bin/bash -l
#SBATCH --job-name=vllm-inference
#SBATCH --time=01:00:00
#SBATCH --partition=gpu
#SBATCH --account=p200981
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --qos=default
#SBATCH --output=logs/vllm-inference_%j.out
#SBATCH --error=logs/vllm-inference_%j.err

echo "Date              = $(date)"
echo "Hostname          = $(hostname -s)"
echo "Working Directory = $(pwd)"

# Load required modules
module add Apptainer

# Pull container if needed
if [ ! -f "vllm_vllm-openai_latest.sif" ]; then
    echo "Pulling container image..."
    apptainer pull docker://vllm/vllm-openai:latest
fi

# Start the service
echo "Starting vllm-inference..."
apptainer exec --nv vllm_vllm-openai_latest.sif python -m vllm.entrypoints.api_server
