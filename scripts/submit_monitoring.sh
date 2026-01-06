#!/bin/bash -l
#SBATCH --job-name=ai_factory_monitoring
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8GB
#SBATCH --time=02:00:00
#SBATCH --qos=default
#SBATCH --partition=gpu
#SBATCH --account=p200981                  # project ID
#SBATCH --output=logs/monitoring-%j.out
#SBATCH --error=logs/monitoring-%j.err

# AI Factory Monitoring Stack - SLURM Job for MeluXina Compute Node
# Self-contained script that starts Prometheus, Grafana, and Pushgateway

echo "================================================"
echo "AI Factory Monitoring Node Starting"
echo "================================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Start Time: $(date)"
echo "================================================"

# Store monitoring node hostname for easy reference
export MONITORING_NODE=$(hostname)
echo ""
echo "*** IMPORTANT: Save this hostname for training jobs ***"
echo "MONITORING_NODE=$MONITORING_NODE"
echo ""
echo "Configure your training jobs with:"
echo "  export PUSHGATEWAY_URL=http://$MONITORING_NODE:9091"
echo ""
echo "To access Grafana from your local machine, run:"
echo "  ssh -L 3000:$MONITORING_NODE:3000 -L 9090:$MONITORING_NODE:9090 <username>@login.lxp. lu"
echo "  Then open: http://localhost:3000"
echo "  Username: admin, Password: admin"
echo "================================================"
echo ""

# Navigate to project directory
cd $SLURM_SUBMIT_DIR || exit 1

# Load required modules
module purge
if module load tools/Singularity 2>/dev/null; then
    echo "✓ Loaded Singularity module"
elif module load Apptainer 2>/dev/null; then
    echo "✓ Loaded Apptainer module"
else
    echo "ERROR: Neither Singularity nor Apptainer module could be loaded"
    echo "Please ensure one of these containerization tools is available on your system"
    exit 1
fi

# Verify singularity command is available
if ! command -v singularity &> /dev/null; then
    echo "ERROR: 'singularity' command not found after loading module"
    exit 1
fi

# Create necessary directories
echo "Creating directory structure..."
mkdir -p logs reports
mkdir -p monitoring_data/{prometheus,grafana,pushgateway}
mkdir -p monitoring_data/grafana/{data,logs,plugins}
mkdir -p monitoring_data/prometheus/data
mkdir -p monitoring/prometheus

# Check for required container images
echo "Checking for container images..."
CONTAINERS_DIR="./containers"
if [ ! -f "$CONTAINERS_DIR/prometheus.sif" ]; then
    echo "ERROR: Prometheus container not found at $CONTAINERS_DIR/prometheus. sif"
    echo "Please build containers first using: ./scripts/build_containers.sh"
    exit 1
fi
if [ ! -f "$CONTAINERS_DIR/grafana.sif" ]; then
    echo "ERROR: Grafana container not found at $CONTAINERS_DIR/grafana.sif"
    exit 1
fi
if [ !  -f "$CONTAINERS_DIR/pushgateway.sif" ]; then
    echo "ERROR:  Pushgateway container not found at $CONTAINERS_DIR/pushgateway.sif"
    exit 1
fi

# Create Prometheus configuration if it doesn't exist
if [ !  -f "monitoring/prometheus/prometheus.yml" ]; then
    echo "Creating Prometheus configuration..."
    cat > monitoring/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs: 
      - targets: ['localhost:9090']

  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets:  ['localhost:9091']

  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']
EOF
    echo "✓ Prometheus configuration created"
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "================================================"
    echo "Shutting down monitoring services..."
    echo "================================================"
    
    if [ !  -z "$PROMETHEUS_PID" ] && kill -0 $PROMETHEUS_PID 2>/dev/null; then
        echo "Stopping Prometheus (PID: $PROMETHEUS_PID)..."
        kill $PROMETHEUS_PID
    fi
    
    if [ ! -z "$GRAFANA_PID" ] && kill -0 $GRAFANA_PID 2>/dev/null; then
        echo "Stopping Grafana (PID: $GRAFANA_PID)..."
        kill $GRAFANA_PID
    fi
    
    if [ ! -z "$PUSHGATEWAY_PID" ] && kill -0 $PUSHGATEWAY_PID 2>/dev/null; then
        echo "Stopping Pushgateway (PID: $PUSHGATEWAY_PID)..."
        kill $PUSHGATEWAY_PID
    fi
    
    echo "Cleanup complete"
    exit 0
}

# Register cleanup function
trap cleanup SIGINT SIGTERM EXIT

# Start Prometheus
echo "================================================"
echo "Starting Prometheus on port 9090..."
echo "================================================"
apptainer run \
  --bind ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro \
  --bind $PWD/monitoring_data/prometheus/data:/prometheus \
  $CONTAINERS_DIR/prometheus.sif \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --web.listen-address=:9090 \
  > logs/prometheus-$SLURM_JOB_ID.log 2>&1 &

PROMETHEUS_PID=$! 
echo "✓ Prometheus started (PID: $PROMETHEUS_PID)"
sleep 5

# Verify Prometheus is running
if ! kill -0 $PROMETHEUS_PID 2>/dev/null; then
    echo "ERROR:  Prometheus failed to start.  Check logs/prometheus-$SLURM_JOB_ID.log"
    exit 1
fi

# Start Pushgateway
echo "================================================"
echo "Starting Pushgateway on port 9091..."
echo "================================================"
apptainer run \
  --bind $PWD/monitoring_data/pushgateway:/data \
  $CONTAINERS_DIR/pushgateway.sif \
  --persistence.file=/data/pushgateway.data \
  --persistence.interval=5m \
  --web.listen-address=:9091 \
  > logs/pushgateway-$SLURM_JOB_ID.log 2>&1 &

PUSHGATEWAY_PID=$!
echo "✓ Pushgateway started (PID: $PUSHGATEWAY_PID)"
sleep 5

# Verify Pushgateway is running
if ! kill -0 $PUSHGATEWAY_PID 2>/dev/null; then
    echo "ERROR:  Pushgateway failed to start.  Check logs/pushgateway-$SLURM_JOB_ID.log"
    exit 1
fi

# Start Grafana
echo "================================================"
echo "Starting Grafana on port 3000..."
echo "================================================"
apptainer run \
  --bind $PWD/monitoring_data/grafana/data:/var/lib/grafana \
  --bind $PWD/monitoring_data/grafana/logs:/var/log/grafana \
  --env GF_PATHS_DATA=/var/lib/grafana \
  --env GF_PATHS_LOGS=/var/log/grafana \
  --env GF_SERVER_HTTP_ADDR=0.0.0.0 \
  --env GF_SERVER_HTTP_PORT=3000 \
  --env GF_SECURITY_ADMIN_USER=admin \
  --env GF_SECURITY_ADMIN_PASSWORD=admin \
  $CONTAINERS_DIR/grafana.sif \
  > logs/grafana-$SLURM_JOB_ID.log 2>&1 &

GRAFANA_PID=$!
echo "✓ Grafana started (PID: $GRAFANA_PID)"
sleep 10

# Verify Grafana is running
if ! kill -0 $GRAFANA_PID 2>/dev/null; then
    echo "ERROR: Grafana failed to start. Check logs/grafana-$SLURM_JOB_ID.log"
    exit 1
fi

# Display status
echo ""
echo "================================================"
echo "✓ All monitoring services are running!"
echo "================================================"
echo ""
echo "Service Status:"
echo "  - Prometheus:   http://$MONITORING_NODE:9090 (PID: $PROMETHEUS_PID)"
echo "  - Pushgateway: http://$MONITORING_NODE:9091 (PID: $PUSHGATEWAY_PID)"
echo "  - Grafana:     http://$MONITORING_NODE:3000 (PID: $GRAFANA_PID)"
echo ""
echo "SSH Port Forwarding Command:"
echo "  ssh -L 3000:$MONITORING_NODE:3000 -L 9090:$MONITORING_NODE:9090 -L 9091:$MONITORING_NODE:9091 <username>@login.lxp.lu"
echo ""
echo "Access URLs (after SSH tunnel):"
echo "  - Grafana:      http://localhost:3000 (admin/admin)"
echo "  - Prometheus:  http://localhost:9090"
echo "  - Pushgateway: http://localhost:9091"
echo ""
echo "For training jobs, set:"
echo "  export PUSHGATEWAY_URL=http://$MONITORING_NODE:9091"
echo ""
echo "================================================"
echo "Monitoring node will run until job time limit or manual cancellation"
echo "To stop:  scancel $SLURM_JOB_ID"
echo "================================================"
echo ""

# Monitor services and keep job alive
echo "Monitoring services health..."
while true; do
    sleep 60
    
    # Check if all services are still running
    if ! kill -0 $PROMETHEUS_PID 2>/dev/null; then
        echo "WARNING: Prometheus has stopped unexpectedly!"
        echo "Check logs/prometheus-$SLURM_JOB_ID. log for details"
        exit 1
    fi
    
    if ! kill -0 $PUSHGATEWAY_PID 2>/dev/null; then
        echo "WARNING: Pushgateway has stopped unexpectedly!"
        echo "Check logs/pushgateway-$SLURM_JOB_ID.log for details"
        exit 1
    fi
    
    if ! kill -0 $GRAFANA_PID 2>/dev/null; then
        echo "WARNING:  Grafana has stopped unexpectedly!"
        echo "Check logs/grafana-$SLURM_JOB_ID.log for details"
        exit 1
    fi
    
    # Print heartbeat every 10 minutes
    if [ $(($(date +%s) % 600)) -lt 60 ]; then
        echo "[$(date)] Services running normally - Prometheus: $PROMETHEUS_PID, Grafana: $GRAFANA_PID, Pushgateway: $PUSHGATEWAY_PID"
    fi
done