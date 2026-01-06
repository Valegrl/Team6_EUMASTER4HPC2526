meluxina_simulation_guide# AI Factory Benchmarking Framework

## Complete Guide to HPC Benchmarking of AI Infrastructure

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Prerequisites and Requirements](#3-prerequisites-and-requirements)
4. [Installation and Setup](#4-installation-and-setup)
5. [Service Configuration](#5-service-configuration)
6. [Running Benchmarks](#6-running-benchmarks)
7. [Monitoring and Visualization](#7-monitoring-and-visualization)
8. [Analyzing Results](#8-analyzing-results)
9. [Supported Services](#9-supported-services)
10. [Advanced Usage](#10-advanced-usage)
11. [Troubleshooting](#11-troubleshooting)
12. [Best Practices](#12-best-practices)

---

## 1. Overview

### Purpose

The AI Factory Benchmarking Framework is a comprehensive, production-ready solution for evaluating the performance of AI infrastructure components on HPC systems. It provides:

- **Unified benchmarking** across diverse AI services (LLMs, vector databases, storage systems)
- **Real-time monitoring** with Prometheus and Grafana integration
- **SLURM integration** for HPC cluster orchestration
- **Modular architecture** supporting extensible service types
- **Reporting** with detailed metrics and visualizations

### Key Features

✅ **Comprehensive Service Support**
- LLM Inference: Ollama, vLLM, Triton
- Vector Databases: ChromaDB, Faiss, Weaviate
- Relational Databases: PostgreSQL
- Object Storage: S3-compatible (MinIO)
- File Storage: POSIX filesystem benchmarking

✅ **Production-Grade Monitoring**
- Prometheus metrics export
- Grafana dashboards
- Real-time performance tracking
- Alert management

✅ **HPC Integration**
- SLURM job scheduling
- Apptainer containerization
- GPU acceleration support
- Multi-node orchestration

✅ **Reporting**
- JSON reports with detailed statistics
- Prometheus-compatible metrics
- HTML visualization (optional)
- CSV export capabilities

---

## 2. Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface                          │
│              (CLI, Recipe Configuration)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 Main Orchestrator                           │
│            (Coordinates all components)                     │
└──┬──────────┬──────────┬──────────┬──────────┬─────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌──────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐
│Middle│ │ Server │ │ Client │ │Monitor │ │Reporter │
│ware  │ │Manager │ │Factory │ │        │ │         │
└───┬──┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬────┘
    │         │          │          │          │
    │         │          │          │          │
    ▼         ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────┐
│              Benchmark Services                  │
│  ┌──────┐ ┌─────┐ ┌────┐ ┌───────┐ ┌────────┐ │
│  │ LLMs │ │ VDB │ │ DB │ │Storage│ │ Triton │ │
│  └──────┘ └─────┘ └────┘ └───────┘ └────────┘ │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│         Monitoring & Storage                     │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐         │
│  │Prometheus│ │Pushgateway│ │ Grafana │         │
│  └──────────┘ └──────────┘ └─────────┘         │
│       ▲            ▲             │               │
│       │            │             ▼               │
│       │            │      ┌───────────┐         │
│       └────────────┴──────│SQLite  DB │         │
│                           └───────────┘         │
└─────────────────────────────────────────────────┘
```

### Component Description

**Main Orchestrator**: Coordinates the complete benchmark workflow from initialization to cleanup.

**Middleware Interface**: Loads and validates recipe configurations, provides service metadata.

**Server Manager**: Manages lifecycle of benchmark services (start, stop, health checks).

**Unified Client Factory**: Creates appropriate specialized clients based on service type.

**Monitor**: Collects and stores performance metrics in SQLite database.

**Reporter**: Generates comprehensive reports in multiple formats (JSON, Prometheus, HTML).

**Prometheus**: Time-series database that scrapes and stores metrics for querying and alerting.

**Pushgateway**: Intermediary service that allows ephemeral and batch jobs to push metrics to Prometheus.

**Grafana**: Visualization and analytics platform for creating dashboards and exploring metrics.

---

## 3. Prerequisites and Requirements

### System Requirements

#### For HPC Deployment (MeluXina)
- **MeluXina Account**: Active account with project allocation
- **SLURM Access**: Ability to submit jobs
- **Apptainer**: Version 1.0+ (available via module at `/apps/.../Apptainer/1.3.6`)
- **Python**: 3.12.3 (via module: `Python/3.12.3-GCCcore-13.3.0`)
- **GPU Access**: For LLM inference benchmarks (partition: gpu)

### Software Dependencies

Core Python packages (automatically installed via `requirements.txt`):
```
PyYAML>=6.0
requests>=2.31.0
numpy>=1.24.0
pandas>=2.0.0
psycopg2-binary>=2.9.0
boto3>=1.28.0
chromadb>=0.4.0
faiss-cpu>=1.7.4
weaviate-client>=3.24.0
prometheus-client>=0.18.0
rich>=13.0.0
matplotlib>=3.7.0
```

---

## 4. Installation and Setup

### 4.1 HPC Installation (MeluXina's compute node)

#### Step 1: Connect to MeluXina

```bash
ssh <username>@login.lxp.lu -p 8822
```

#### Step 2: Navigate to Project Directory

```bash
cd $PROJECT/p200981  # project ID
```

#### Step 3: Load Required Modules

```bash
module purge
module add Apptainer
module load Python/3.12.3-GCCcore-13.3.0
```

**Verification:**
```bash
apptainer --version
python --version 
```

> **Note:** MeluXina provides Apptainer 1.3.6 at `/apps/.../Apptainer/1.3.6`

#### Step 4: Clone Repository

```bash
git clone https://github.com/Valegrl/Team6_EUMASTER4HPC2526.git
cd Team6_EUMASTER4HPC2526
```

#### Step 5: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 6: Pull Service Containers (Apptainer)

**Convert Docker Images to Apptainer Images:**

Apptainer can directly pull Docker images and convert them to Apptainer SIF (Singularity Image Format) files:

```bash
# Create containers directory
mkdir -p containers
cd containers

# Pull AI service containers
apptainer pull ollama.sif docker://ollama/ollama
apptainer pull vllm.sif docker://vllm/vllm-openai:latest
apptainer pull chromadb.sif docker://chromadb/chroma:latest
apptainer pull postgres.sif docker://postgres:16
apptainer pull minio.sif docker://minio/minio:latest
apptainer pull weaviate.sif docker://semitechnologies/weaviate:latest

# Pull monitoring stack containers
apptainer pull grafana.sif docker://grafana/grafana:latest
apptainer pull prometheus.sif docker://prom/prometheus:latest
apptainer pull pushgateway.sif docker://prom/pushgateway:latest

cd ..
```

**Alternative - Use Pull Script:**
```bash
./scripts/pull_containers.sh
```

**Verification:**
```bash
ls -lh containers/*.sif
```

Expected output: Multiple `.sif` files, each 100MB-2GB in size.

---

### 4.2 Monitoring Stack Setup on HPC Compute Nodes

> **Why Use Compute Node Monitoring?**
> 
> ✅ **No SSH tunneling needed** for metrics collection  
> ✅ **Faster network** - internal high-speed interconnect  
> ✅ **No firewall issues** - compute nodes communicate directly  
> ✅ **Better resource allocation** - dedicated compute resources  

This section shows how to set up Prometheus, Grafana, and Pushgateway on a dedicated MeluXina compute node using Apptainer.

#### Architecture Overview

```
┌─────────────────────────────┐    ┌──────────────────────────────┐
│ Compute Node 1 (Training)   │    │ Compute Node 2 (Monitoring)  │
│                             │    │                              │
│  ┌──────────────────────┐  │    │  ┌────────────────────────┐ │
│  │ Benchmark/Training   │  │    │  │ Prometheus :9090       │ │
│  │ Job                  │  │    │  │ (metrics storage)      │ │
│  └──────────────────────┘  │    │  └────────────────────────┘ │
│           │                 │    │             ▲               │
│           │ metrics         │    │             │               │
│           ▼                 │    │  ┌────────────────────────┐ │
│  ┌──────────────────────┐  │    │  │ Pushgateway :9091      │ │
│  │ Metrics Exporter     │──┼────┼─▶│ (receives metrics)     │ │
│  │ (pushes to :9091)    │  │    │  └────────────────────────┘ │
│  └──────────────────────┘  │    │             │               │
│                             │    │             ▼               │
└─────────────────────────────┘    │  ┌────────────────────────┐ │
                                   │  │ Grafana :3000          │ │
                                   │  │ (visualization)        │ │
                                   │  └────────────────────────┘ │
                                   └──────────────────────────────┘
                                                │
                                                │ SSH tunnel (view only)
                                                ▼
                                   ┌──────────────────────────────┐
                                   │ Your Local Machine           │
                                   │ http://localhost:3000        │
                                   └──────────────────────────────┘
```

#### Step 1: Start Monitoring Node

On the MeluXina login node:

```bash
cd $PROJECT/p200981/Team6_EUMASTER4HPC2526 

# Submit the monitoring job to SLURM
sbatch scripts/submit_monitoring.sh
```

**Optional - Set Custom Grafana Credentials:**
```bash
# Must be done before submitting the job
export GRAFANA_ADMIN_USER=myuser
export GRAFANA_ADMIN_PASSWORD=mysecurepass
sbatch scripts/submit_monitoring.sh
```

The job will:
- Request a compute node from the `gpu` partition
- Load Apptainer module
- Pull and start Prometheus, Grafana, and Pushgateway containers
- Keep running for 2 hours (configurable via `#SBATCH --time` in the script)

#### Step 2: Get the Monitoring Node Hostname

After submitting, wait ~30 seconds for the job to start, then:

```bash
# Check job status
squeue -u $USER

# Example output:
# JOBID   PARTITION   NAME                  NODELIST
# 123456  gpu         ai_factory_monitoring mel2345
#                                           ^^^^^^^^ This is your monitoring node
```

**Alternative - View Job Output:**
```bash
cat logs/monitoring-<job-id>.out | grep MONITORING_NODE
# Output: MONITORING_NODE=mel2345
```

**💡 Save this hostname** - you'll need it for all training jobs!

#### Step 2 (Manual alternative): Running Apptainer Containers on Compute Nodes

When running benchmark services (Grafana, Prometheus, ChromaDB, etc.) on compute nodes, use Apptainer with proper flags:

**Basic Apptainer Run Command:**
```bash
apptainer run \
  --bind $HOME/data:/data \
  --env SERVICE_PORT=8080 \
  service.sif
```

**For GPU-Accelerated Services:**
```bash
# Use --nv flag to enable NVIDIA GPU support
apptainer run --nv \
  --bind $HOME/data:/data \
  --env CUDA_VISIBLE_DEVICES=0 \
  chromadb.sif
```

**Example: Running Grafana on Compute Node**
```bash
apptainer run \
  --bind $HOME/grafana/data:/var/lib/grafana \
  --bind $HOME/grafana/logs:/var/log/grafana \
  --env GF_PATHS_DATA=/var/lib/grafana \
  --env GF_PATHS_LOGS=/var/log/grafana \
  --env GF_PATHS_PLUGINS=/var/lib/grafana/plugins \
  --env GF_SERVER_HTTP_ADDR=0.0.0.0 \
  --env GF_SERVER_HTTP_PORT=3000 \
  containers/grafana.sif
```

**Example: Running Prometheus**
```bash
apptainer run \
  --bind ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro \
  --bind $HOME/prometheus/data:/prometheus \
  containers/prometheus.sif \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --web.listen-address=:9090
```

> **Note:** The `submit_monitoring.sh` script automates all of this for you.

#### Step 3: Configure Training Jobs with Monitoring

Edit your training/benchmark job scripts to send metrics to the monitoring node:

```bash
#!/bin/bash
#SBATCH --job-name=my_benchmark
#SBATCH --nodes=1
#SBATCH --time=01:00:00
#...

# Set monitoring node (replace mel2345 with your actual node)
export MONITORING_NODE=mel2345
export PUSHGATEWAY_URL="http://${MONITORING_NODE}:9091"

# Load modules
module purge
module add Apptainer
module load Python/3.12.3-GCCcore-13.3.0

# Run benchmark with monitoring
cd $SLURM_SUBMIT_DIR
source venv/bin/activate

python src/main.py \
    --recipe recipe.yml \
    --pushgateway $PUSHGATEWAY_URL
```

Then submit:
```bash
sbatch your_training_script.sh
```

#### Step 5: Access Grafana from Your Local Machine

Create a double SSH tunnel from your local machine to the compute node via the login node:

```bash
# On your local machine (replace mel2345 with your monitoring node)
ssh -L 3000:mel2345:3000 -L 9090:mel2345:9090 -L 9091:mel2345:9091 <username>@login.lxp.lu -p 8822
```

Explanation:
- `3000:mel2345:3000` - Forward Grafana port from compute node to your laptop
- `9090:mel2345:9090` - Forward Prometheus port
- `9091:mel2345:9091` - Forward Pushgateway port
- `<username>@login.lxp.lu` - Your MeluXina credentials
- `-p 8822` - MeluXina SSH port

Then open in your browser:
- **Grafana**: http://localhost:3000 (login: admin / admin)
- **Prometheus**: http://localhost:9090
- **Pushgateway**: http://localhost:9091

#### Step 6: Monitor and Manage Services

**Check Monitoring Stack Status:**
```bash
# SSH to monitoring node
ssh mel2345  # Replace with your node

# List running Apptainer instances
singularity instance list

# Expected output:
# INSTANCE NAME    PID      IMAGE
# ai_grafana       12345    /path/to/grafana.sif
# ai_prometheus    12346    /path/to/prometheus.sif
# ai_pushgateway   12347    /path/to/pushgateway.sif
```

**Stop Monitoring Stack:**
```bash
# Option 1: Cancel the SLURM job (recommended)
scancel <job-id>

# Option 2: Stop services manually (if job still running)
ssh mel2345
cd $PROJECT/p200981/Team6_EUMASTER4HPC2526
./scripts/stop_monitoring_compute.sh
```

#### Complete Workflow Example

```bash
# === ON MELUXINA LOGIN NODE ===

# 1. Submit monitoring job
cd $PROJECT/p200981/Team6_EUMASTER4HPC2526
sbatch scripts/submit_monitoring.sh
# Note the job ID: 123456

# 2. Wait ~30 seconds, then get monitoring node
cat logs/monitoring-<job-id>.out | grep MONITORING_NODE
# Output: MONITORING_NODE=mel2345

# 3. Submit benchmark job
sbatch scripts/run_benchmark.sh  # Already configured to use monitoring

# === ON YOUR LOCAL MACHINE ===

# 4. Create SSH tunnel to view dashboards
ssh -L 3000:mel2345:3000 -L 9090:mel2345:9090 -L 9091:mel2345:9091  <username>@login.lxp.lu -p 8822

# 5. Open browser to http://localhost:3000
# Login: admin / admin
# Watch your metrics in real-time!
```

#### Troubleshooting Monitoring Setup

**Problem: Can't connect to monitoring services**

Solution:
1. Verify monitoring job is running: `squeue -u $USER`
2. Check node hostname matches: `cat logs/monitoring-<job-id>.out`
3. Ensure firewall rules allow inter-node communication (usually enabled by default on MeluXina)

**Problem: Metrics not appearing in Grafana**

Solution:
1. Verify `PUSHGATEWAY_URL` is set correctly in training job
2. Check Pushgateway is receiving data: 
   ```bash
   curl http://mel2345:9091/metrics  # Replace mel2345
   ```
3. Verify Prometheus is scraping Pushgateway:
   - Open http://localhost:9090 (via SSH tunnel)
   - Go to Status → Targets
   - Check "pushgateway" target is UP

**Problem: SSH tunnel not working**

Solution:
1. Verify monitoring node hostname is correct
2. Try with full domain: `ssh -L 3000:mel2345.lxp.lu:3000 <username>@login.lxp.lu -p 8822`
3. Check if you can SSH to the compute node: `ssh mel2345`

#### Tips for Monitoring

💡 **Tip 1**: Keep the monitoring job running for the duration of your experiments  
💡 **Tip 2**: You can run multiple training jobs simultaneously, all sending to the same monitoring node  
💡 **Tip 3**: Increase the monitoring job time limit for long experiments: `#SBATCH --time=24:00:00`  
💡 **Tip 4**: Save the monitoring node hostname in a file for easy reference across sessions  

```bash
# Save monitoring node to file
echo "mel2345" > .monitoring_node

# Use in scripts
MONITORING_NODE=$(cat .monitoring_node)
export PUSHGATEWAY_URL="http://${MONITORING_NODE}:9091"
```

---

## 5. Service Configuration

### 5.1 Understanding recipe.yml

The `recipe.yml` file is the **configuration source of truth**. It defines:
- Which services to benchmark
- Load patterns (client count, RPS, duration)
- Resource requirements (SLURM parameters)
- Service-specific settings

### 5.2 Basic Configuration Structure

```yaml
benchmark:
  name: "My Benchmark"
  description: "Description of this benchmark run"
  duration: 600  # Total suite duration

global:
  log_level: INFO
  metrics_db: metrics.db
  reports_dir: reports
  logs_dir: logs
  pushgateway_url: http://localhost:9091  # Optional

services:
  - service_name: unique-service-id
    service_type: <type>
    # ... service-specific configuration
```

### 5.3 Service Types and Configuration

#### LLM Inference Services

**Ollama:**
```yaml
- service_name: ollama-llama2
  service_type: ollama
  port: 11434
  model: llama2
  client_count: 5
  requests_per_second: 10
  duration: 300
  slurm:
    partition: gpu
    account: p200981
```

**vLLM:**
```yaml
- service_name: vllm-opt
  service_type: vllm
  port: 8000
  model: facebook/opt-125m
  client_count: 10
  requests_per_second: 20
  duration: 300
```

#### Vector Databases

**ChromaDB:**
```yaml
- service_name: chromadb
  service_type: vectordb
  backend: chromadb
  port: 8000
  dimension: 384
  operation_mix:
    insert: 0.3
    search: 0.5
    update: 0.1
    delete: 0.1
  batch_size: 10
  search_k: 10
```

**Faiss (in-memory):**
```yaml
- service_name: faiss
  service_type: vectordb
  backend: faiss
  dimension: 384
  operation_mix:
    insert: 0.4
    search: 0.6
```

#### Databases

**PostgreSQL:**
```yaml
- service_name: postgresql
  service_type: database
  backend: postgresql
  host: localhost
  port: 5432
  database: benchmark
  user: postgres
  password: benchmark
  operation_mix:
    select: 0.4
    insert: 0.3
    update: 0.2
    delete: 0.1
```

#### Object Storage

**MinIO (S3-compatible):**
```yaml
- service_name: minio-s3
  service_type: s3
  endpoint_url: http://localhost:9000
  access_key: minioadmin
  secret_key: minioadmin
  bucket_name: benchmark-bucket
  operation_mix:
    put: 0.4
    get: 0.4
    list: 0.1
    delete: 0.1
  object_sizes:
    1KB: 0.3
    10KB: 0.3
    100KB: 0.2
    1MB: 0.15
    10MB: 0.05
```

#### File Storage

```yaml
- service_name: file-storage
  service_type: file_storage
  base_path: /tmp/benchmark_storage
  operation_mix:
    write: 0.4
    read: 0.4
    stat: 0.1
    delete: 0.1
  file_sizes:
    1KB: 0.2
    10KB: 0.2
    100KB: 0.2
    1MB: 0.2
    10MB: 0.2
```

### 5.4 SLURM Configuration

```yaml
slurm:
  partition: gpu           # or 'cpu'
  account: p200981         # Your project account
  time: "01:00:00"         # HH:MM:SS format
  nodes: 1
  ntasks: 1
  qos: default
  gres: gpu:1              # Optional: GPU resources
```

**Key Parameters:**
- **partition**: `gpu` for LLM services, `cpu` for databases
- **account**: Your project allocation ID
- **time**: Maximum runtime (add 20-30% buffer)
- **gres**: GPU resources (e.g., `gpu:1`, `gpu:4`)

---

## 6. Running Benchmarks

### 6.1 Local Benchmark Execution

```bash
# Activate virtual environment
source venv/bin/activate

# Run benchmark with default recipe
python src/main.py --recipe recipe.yml

# Run with comprehensive recipe
python src/main.py --recipe recipe_comprehensive.yml
```

### 6.2 HPC Batch Execution (SLURM)

```bash
# Submit batch job
sbatch scripts/run_benchmark.sh

# Monitor job status
squeue -u $USER

# View output (replace JOBID)
tail -f logs/benchmark_JOBID.out
```

### 6.3 Interactive SLURM Session

```bash
# Request interactive session
salloc --partition=gpu --account=p200981 --time=01:00:00 --nodes=1

# Once allocated, run benchmark
module add Apptainer
module load Python/3.12.3-GCCcore-13.3.0
source venv/bin/activate
python src/main.py --recipe recipe.yml

# Exit when done
exit
```

### 6.4 Parallel vs Sequential Benchmarking

By default, benchmarks run **in parallel** (up to 10x faster):

```bash
# Parallel (default) - 10 services in ~5 min instead of ~50 min
python src/main.py --recipe recipe_comprehensive.yml

# Customize workers
python src/main.py --recipe recipe_comprehensive.yml --max-workers 10

# Sequential (for debugging)
python src/main.py --recipe recipe_comprehensive.yml --sequential
```

**Note:** Reduce `--max-workers` if experiencing high CPU/memory usage.

---

## 7. Monitoring and Visualization

> **For HPC Deployment:** See Section 4.3 for complete Apptainer-based monitoring setup on MeluXina compute nodes.

### 7.1 Monitoring Options Overview

You have two options for running the monitoring stack:


#### MeluXina Compute Node Monitoring

**When to use:** Production HPC deployment with Apptainer containerization.

**Quick Start:**
```bash
# 1. Submit monitoring job (on MeluXina login node)
cd $PROJECT/p200981/Team6_EUMASTER4HPC2526
sbatch scripts/submit_monitoring.sh

# 2. Get monitoring node hostname
cat logs/monitoring-<job-id>.out | grep MONITORING_NODE

# 3. Configure your benchmark jobs to use this monitoring node
export MONITORING_NODE=mel2345  # Replace with actual node
export PUSHGATEWAY_URL="http://${MONITORING_NODE}:9091"

# 4. View dashboards from local machine via SSH tunnel
ssh -L 3000:mel2345:3000 -L 9090:mel2345:9090 -L 9091:mel2345:9091  <username>@login.lxp.lu -p 8822
```

**📖 Complete Instructions:** See **Section 4.3** for detailed setup, troubleshooting, and examples.

### 7.2 Accessing Grafana

Once you have Grafana running (either locally or via SSH tunnel from compute node):

1. Open http://localhost:3000
2. Login: `admin` / `admin` (default credentials)
3. Navigate to "AI Factory Benchmarking Dashboard"

**Dashboard Panels:**
- Request Rate (Throughput)
- Success Rate Gauge
- Response Time (Latency) with percentiles
- Total Requests Counter
- Failed Requests Counter
- Requests by Service (Pie Chart)
- Success vs Failure (Stacked Bar)

### 7.3 Querying Prometheus

Access Prometheus at http://localhost:9090

**Example Queries:**
```promql
# Request rate
rate(benchmark_requests_total[1m])

# Average latency
benchmark_request_duration_seconds_sum / benchmark_request_duration_seconds_count

# Success rate
(benchmark_requests_successful / benchmark_requests_total) * 100

# P95 latency
histogram_quantile(0.95, rate(benchmark_request_duration_seconds_bucket[5m]))
```

### 7.4 Exporting Metrics

**To Prometheus format:**
```bash
python src/monitoring/prometheus_exporter.py <benchmark_id> -o metrics.prom
```

**To Pushgateway:**
```bash
python src/monitoring/prometheus_exporter.py <benchmark_id> \
  --push --gateway-url http://localhost:9091
```

### 7.5 Complete Monitoring Workflow: Step-by-Step Guide

This section provides a complete end-to-end workflow for setting up monitoring, pushing metrics, and visualizing results in Grafana.

#### Step 1: Push Metrics to Pushgateway

After running a benchmark, push the collected metrics to Pushgateway for visualization:

```bash
# Navigate to your working directory
cd /project/scratch/p200981/u103225

# Set monitoring node environment variable (replace mel2110 with your monitoring node)
export MONITORING_NODE=mel2110
export PUSHGATEWAY_URL="http://${MONITORING_NODE}:9091"

# Push metrics to Pushgateway
python src/monitoring/prometheus_exporter.py benchmark_1767688819 \
  --push \
  --gateway-url $PUSHGATEWAY_URL
```

**Alternative with explicit job name:**
```bash
cd /project/scratch/p200981/u103225

python src/monitoring/prometheus_exporter.py benchmark_1767688819 \
  --push \
  --gateway-url http://mel2110:9091 \
  --job ai_factory_benchmark
```

**Expected output:**
```
✓ Metrics pushed successfully!
```

#### Step 2: Access Grafana & Prometheus from Your Local Machine

On your local machine, open a new terminal and create an SSH tunnel to access the monitoring services:

```bash
# SSH tunnel command (replace mel2110 with your monitoring node and <username> with your MeluXina username)
ssh -L 3000:mel2110:3000 -L 9090:mel2110:9090 -L 9091:mel2110:9091 <username>@login.lxp.lu -p 8822
```

This command forwards:
- Port 3000: Grafana dashboard
- Port 9090: Prometheus metrics browser
- Port 9091: Pushgateway metrics viewer

**Keep this SSH tunnel open** while you access the dashboards.

#### Step 3: Verify Metrics in Prometheus

1. **Open Prometheus:** Navigate to http://localhost:9090 in your browser
2. **Go to the Graph tab**
3. **Try these queries to verify metrics:**

   - **Total requests:**
     ```promql
     benchmark_requests_total
     ```

   - **Successful requests:**
     ```promql
     benchmark_requests_successful
     ```

   - **Request rate (over 5 minutes):**
     ```promql
     rate(benchmark_requests_total[5m])
     ```

   - **Average latency:**
     ```promql
     benchmark_request_duration_seconds_sum / benchmark_request_duration_seconds_count
     ```

   - **P95 latency:**
     ```promql
     histogram_quantile(0.95, rate(benchmark_request_duration_seconds_bucket[5m]))
     ```

#### Step 4: Verify Pushgateway

1. **Open Pushgateway:** Navigate to http://localhost:9091 in your browser
2. You should see your metrics listed there with the job name and instance labels
3. Verify that the metrics match your benchmark run

#### Step 5: Create Grafana Dashboard

1. **Open Grafana:** Navigate to http://localhost:3000 in your browser

2. **Login:** Use credentials `admin` / `admin` (default)
   - You may be prompted to change the password on first login

3. **Add Prometheus as Data Source:**
   - Click ⚙️ (Configuration) → **Data Sources**
   - Click **"Add data source"**
   - Select **"Prometheus"**
   - In the **URL** field, enter: `http://mel2110:9090` (replace mel2110 with your monitoring node)
   - Scroll down and click **"Save & Test"**
   - You should see: "Data source is working"

4. **Create Dashboard or upload it from `Team6_EUMASTER4HPC2526/monitoring/grafana/dashboards/ai-factory-benchmark.json`:**
   - Click **+** → **Create** → **Dashboard**
   - Click **"Add new panel"**

   **Add Metrics Panels:**

   **Panel 1: Request Rate**
   - Query: `rate(benchmark_requests_total[1m])`
   - Visualization: Graph
   - Title: "Request Rate (RPS)"

   **Panel 2: Success Rate**
   - Query: `(benchmark_requests_successful / benchmark_requests_total) * 100`
   - Visualization: Gauge
   - Title: "Success Rate (%)"
   - Set thresholds: Green > 95%, Yellow > 90%, Red < 90%

   **Panel 3: Response Time**
   - Query: `benchmark_request_duration_seconds_sum / benchmark_request_duration_seconds_count`
   - Visualization: Graph
   - Title: "Average Response Time (seconds)"

   **Panel 4: Request Count**
   - Query: `benchmark_requests_total`
   - Visualization: Stat
   - Title: "Total Requests"

   **Panel 5: Failed Requests**
   - Query: `benchmark_requests_failed`
   - Visualization: Stat
   - Title: "Failed Requests"

6. **Save Dashboard:**
   - Click the **Save** icon (💾) in the top right
   - Enter a name: "AI Factory Benchmarking Dashboard"
   - Click **Save**

#### Troubleshooting the Monitoring Workflow

**Problem: Cannot connect to Prometheus/Grafana**

- Verify SSH tunnel is active: Check that your SSH connection is still open
- Verify monitoring node: Ensure you're using the correct monitoring node hostname
- Check monitoring job status: `squeue -u $USER` to verify the monitoring job is running

**Problem: No metrics visible in Prometheus**

- Verify metrics were pushed: Check the output from the prometheus_exporter.py script
- Check Pushgateway: Visit http://localhost:9091 to see if metrics are there
- Verify Prometheus is scraping Pushgateway: In Prometheus, go to Status → Targets

**Problem: Grafana cannot connect to Prometheus**

- Verify data source URL: Should be `http://mel2110:9090` (your monitoring node, not localhost)
- Check network connectivity from Grafana to Prometheus (both should be on the same compute node)
- Verify Prometheus is running: `curl http://mel2110:9090/-/healthy`

**Problem: Metrics pushed but not appearing in Grafana**

- Refresh Grafana dashboard
- Check time range in Grafana (top right) - ensure it covers when you pushed metrics
- Verify query syntax in panel settings
- Check Prometheus query in the Explore tab first

---

## 8. Analyzing Results

### 8.1 Locating Results

```bash
# List reports
ls -lt reports/

# View latest report
cat reports/benchmark_*_report.json | python -m json.tool | less
```

### 8.2 Report Structure

```json
{
  "benchmark_id": "benchmark_1234567890",
  "timestamp": "2025-01-04T12:00:00",
  "summary": {
    "total_requests": 3000,
    "successful_requests": 2950,
    "failed_requests": 50,
    "success_rate": 98.33,
    "total_duration": 300.5
  },
  "timing": {
    "avg_duration": 0.523,
    "median_duration": 0.501,
    "min_duration": 0.234,
    "max_duration": 2.145,
    "stddev": 0.178
  },
  "percentiles": {
    "p50": 0.501,
    "p90": 0.687,
    "p95": 0.812,
    "p99": 1.234
  },
  "services": {
    "service-name": {
      "total_requests": 3000,
      "success_rate": 98.33,
      "throughput": 9.98,
      "timing": {...}
    }
  }
}
```

### 8.3 Querying Metrics Database

```bash
sqlite3 metrics.db << EOF
-- Summary statistics
SELECT 
    service_name,
    COUNT(*) as total,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
    AVG(request_duration) as avg_duration
FROM metrics
GROUP BY service_name;
EOF
```

### 8.4 Comparing Benchmarks

```bash
# Compare multiple runs
for report in reports/benchmark_*_report.json; do
    echo "=== $(basename $report) ==="
    jq '.summary.success_rate, .timing.avg_duration' $report
done
```

---

## 9. Supported Services

### 9.1 LLM Inference

| Service | Type    | GPU | Models Supported        |
|---------|---------|-----|-------------------------|
| Ollama  | HTTP    | ✓   | Llama2, Mistral, etc.  |
| vLLM    | HTTP    | ✓   | HuggingFace models     |
| Triton  | gRPC/HTTP| ✓  | TensorRT, PyTorch, etc.|

### 9.2 Vector Databases

| Database  | Backend Type | GPU | Features                    |
|-----------|--------------|-----|----------------------------|
| ChromaDB  | HTTP         | ✓   | Full CRUD, Collections     |
| Faiss     | In-memory    | ✓   | Fast similarity search, GPU acceleration |
| Weaviate  | HTTP         | ✓   | GraphQL, semantic search, GPU-accelerated |

### 9.3 Traditional Databases

| Database    | Protocol | GPU | Operations Supported       |
|-------------|----------|-----|---------------------------|
| PostgreSQL  | psycopg2 | ✓   | SELECT, INSERT, UPDATE, DELETE|

### 9.4 Storage Systems

| System       | Protocol | GPU | Operations                |
|--------------|----------|-----|--------------------------|
| MinIO (S3)   | S3 API   | ✓   | PUT, GET, LIST, DELETE   |
| File Storage | POSIX    | ✓   | Read, Write, Stat, Delete|

---

## 10. Advanced Usage

### 10.1 Custom Service Implementation

Create a new client in `src/client/<service>_client.py`:

```python
from dataclasses import dataclass

@dataclass
class CustomRequestResult:
    timestamp: float
    duration: float
    success: bool
    error: Optional[str] = None

class CustomBenchmarkClient:
    def __init__(self, config: Dict[str, Any]):
        # Initialize your client
        pass
    
    def connect(self):
        # Establish connection
        return True
    
    def execute_operation(self):
        # Perform benchmark operation
        return CustomRequestResult(...)
```

Register in `unified_client.py`:
```python
elif self.service_type == 'custom':
    self.client = CustomBenchmarkClient(self.service_config)
```

### 10.2 Multi-Node Benchmarks

```yaml
slurm:
  nodes: 4
  ntasks-per-node: 1
```

### 10.3 GPU Configuration

All services in the AI Factory Benchmarking Framework now support GPU acceleration for enhanced performance:

**LLM Inference Services**: Ollama, vLLM, and Triton utilize GPUs for model inference
**Vector Databases**: ChromaDB, Faiss, and Weaviate leverage GPU for accelerated similarity search and indexing
**Database Systems**: PostgreSQL can use GPU for query acceleration  
**Storage Systems**: MinIO and File Storage can benefit from GPU-accelerated I/O operations

Example GPU configuration:
```yaml
slurm:
  partition: gpu
  gres: gpu:1    # Request 1 GPU (use gpu:4 for 4 GPUs)
  ntasks: 1      # Number of tasks
```

For containers, use the `--nv` flag with Apptainer to enable NVIDIA GPU support:
```bash
apptainer run --nv chromadb.sif
apptainer run --nv postgres.sif
```

### 10.4 Custom Metrics

Extend `MetricsInterceptor` in `src/interceptor/interceptor.py`.

---

## 11. Troubleshooting

### 11.1 Common Issues

**Issue: "docker: command not found" or "docker-compose not found" on MeluXina**

This is expected! Docker is not available on HPC systems.

**Solution:**
- Use Apptainer instead (see Section 4.2 and 4.3)
- The monitoring stack scripts automatically detect the environment
- On compute nodes: Use `scripts/submit_monitoring.sh` which uses Apptainer
- For local development: Use `scripts/start_monitoring.sh` which uses Docker

**Issue: "Cannot connect to Docker daemon" on HPC**

This is expected! There is no Docker daemon on HPC systems.

**Solution:**
- HPC systems don't have Docker daemons for security reasons
- Use Apptainer which doesn't require a daemon process
- Follow the HPC installation instructions in Section 4.2

**Issue: Job stays in PENDING**
```bash
# Check reason
squeue -u $USER --start

# Check partition availability
sinfo -p gpu
```

**Issue: Service connection failed**
```bash
# Check service logs
grep -i error logs/benchmark_*.log

# Verify container is running (use Apptainer on HPC)
apptainer exec containers/service.sif <command>

# Or check Singularity instances
singularity instance list
```

**Issue: Out of memory**
```bash
# Request more memory
sbatch --mem=64G scripts/run_benchmark.sh

# Or use smaller model/dataset
```

**Issue: Apptainer/Singularity instances not starting**
```bash
# Check if module is loaded
module list | grep -i apptainer

# Load Apptainer module if needed
module add Apptainer

# Check for existing instances that might conflict
singularity instance list

# Stop conflicting instances
singularity instance stop <instance_name>
```

### 11.2 Debugging

Enable debug logging:
```yaml
global:
  log_level: DEBUG
```

View detailed logs:
```bash
tail -f logs/benchmark_*.log
```

---

## 12. Best Practices

### 12.1 Resource Management

✅ **Do:**
- Request only needed resources
- Use appropriate partition (GPU vs CPU)
- Set realistic time limits
- Clean up old logs regularly

❌ **Don't:**
- Run on login nodes
- Request excessive resources
- Leave services running after benchmarks

### 12.2 Benchmarking Methodology

1. **Warm-up**: Run short test first
2. **Multiple runs**: Average 3-5 runs
3. **Control variables**: Change one thing at a time
4. **Statistical significance**: Use longer durations (300-600s)

### 12.3 Configuration Management

```bash
# Version control configurations
git add recipe.yml
git commit -m "Benchmark config for LLM comparison"

# Create templates
cp recipe.yml recipes/recipe_llm_light.yml
```

### 12.4 Data Management

```bash
# Organize results
mkdir -p results/2025-01-04
mv reports/*.json results/2025-01-04/

# Archive old data
tar -czf results_2025-01.tar.gz results/2025-01-*
```

