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

# Capture the compute node name
export COMPUTE_NODE=$(hostname -s)
echo "Compute Node      = $COMPUTE_NODE"
export SERVICE_PORT=11434
echo "Service Port      = $SERVICE_PORT"

# Export node info to a file that can be read by other processes
mkdir -p $HOME/.cache/service_endpoints
echo "$COMPUTE_NODE:$SERVICE_PORT" > $HOME/.cache/service_endpoints/ollama-llama2_endpoint.txt
echo "Endpoint info saved to: $HOME/.cache/service_endpoints/ollama-llama2_endpoint.txt"
echo "LS of endpoint folder:"
ls $HOME/.cache/service_endpoints/
echo "Endpoint content:"
cat $HOME/.cache/service_endpoints/ollama-llama2_endpoint.txt


# Load required modules
module add Apptainer


# Using existing container image
echo "Container image: containers/ollama_latest.sif"
if [ ! -f "containers/ollama_latest.sif" ]; then
    echo "ERROR: Container file not found: containers/ollama_latest.sif"
    exit 1
fi

# Start the service in background
echo "Starting ollama-llama2..."
apptainer exec --nv containers/ollama_latest.sif ollama serve &
SERVICE_PID=$!
echo "Service started with PID: $SERVICE_PID"

# Wait for service to be ready
echo "Waiting for service to be ready..."
sleep 10

# Verify service is running (simple check)
if ps -p $SERVICE_PID > /dev/null; then
    echo "Service is running"
    
    # Try to connect to verify it's listening
    if command -v curl &> /dev/null; then
        if curl -s http://localhost:$SERVICE_PORT/ > /dev/null 2>&1; then
            echo "Service is responding on port $SERVICE_PORT"
        else
            echo "WARNING: Service may not be ready on port $SERVICE_PORT"
        fi
    fi
else
    echo "ERROR: Service failed to start"
    exit 1
fi

# Keep the service running (wait for it or run indefinitely)
echo "Service is running. Connect to it at: http://$COMPUTE_NODE:$SERVICE_PORT"
echo "Press Ctrl+C or use 'scancel' to stop the service"
wait $SERVICE_PID
