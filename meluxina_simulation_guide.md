# Complete Guide: Running Benchmarks/Simulations on MeluXina

---

## Table of Contents

1. [Purpose](#1-Purpose)
2. [Prerequisites and Access](#2-prerequisites-and-access)
3. [Initial Connection and Environment Setup](#3-initial-connection-and-environment-setup)
4. [Repository Setup](#4-repository-setup)
5. [Building Service Containers](#5-building-service-containers)
6. [Configuring Your Benchmark](#6-configuring-your-benchmark)
7. [Validating the Environment](#7-validating-the-environment)
8. [Running Your First Test Benchmark](#8-running-your-first-test-benchmark)
9. [Submitting Full-Scale Benchmarks](#9-submitting-full-scale-benchmarks)
10. [Monitoring Execution](#10-monitoring-execution)
11. [Analyzing Results](#11-analyzing-results)
12. [Exporting Metrics](#12-exporting-metrics)
13. [Troubleshooting Common Issues](#13-troubleshooting-common-issues)
14. [Advanced Configuration](#14-advanced-configuration)
15. [Best Practices](#15-best-practices)

---

## 1. Purpose
This guide provides a complete, step-by-step walkthrough for running benchmarks of AI Factory services on the MeluXina supercomputer. Each step is explained with its purpose and meaning.

---

## 2. Prerequisites and Access

### Required Access and Accounts

**What you need**:
- MeluXina HPC account
- Project allocation (e.g., `p200981`)
- SSH access credentials

**Why**: MeluXina is the Luxembourg supercomputer where you'll run the benchmarks. The project allocation tracks your resource usage.

**How to check**:
```bash
# After connecting (see next section)
sacctmgr show assoc where user=$USER
```

### Required Knowledge

**Helpful to know** (but not mandatory):
- Basic Linux command line operations
- Understanding of SLURM job scheduling
- Familiarity with containerization concepts
- Basic Python knowledge

**Why**: The framework automates most complexity, but understanding these concepts helps troubleshoot issues.

---

## 3. Initial Connection and Environment Setup

### Step 3.1: Connect to MeluXina

**Command**:
```bash
ssh <your_username>@login.lxp.lu
```

**What this does**: Connects you to the MeluXina login node, which is the entry point for all HPC operations.

**Why the login node**: Login nodes are for compiling code, managing files, and submitting jobs. The actual benchmarks will run on compute nodes (allocated by SLURM).

### Step 3.2: Navigate to Project Directory

**Command**:
```bash
cd $PROJECT/p200981
# Or your specific project ID
```

**What this does**: Takes you to your project's storage space on MeluXina.

**Why**: The `$PROJECT` directory is:
- Shared among project members
- Has adequate storage space
- Backed up regularly
- Accessible from all compute nodes
- Suitable for long-term data storage

**Verification**:
```bash
pwd  # Should show: /project/home/p200981/...
echo $PROJECT  # Should show your project path
```

### Step 3.3: Load Required Modules

**Commands**:
```bash
module purge
module add Apptainer
module load Python/3.12.3-GCCcore-13.3.0 
```

**What this does**:
- `module purge`: Clears any previously loaded modules to avoid conflicts
- `module add Apptainer`: Adds the containerization tool for running services
- `module load Python`: Loads Python 3.12.3 with required libraries

**Why each module**:
- **Apptainer**: Runs containerized services (Ollama, vLLM, ChromaDB, PostgreSQL) in HPC environment
- **Python 3.12.3**: Required for the benchmarking framework code

**Verification**:
```bash
apptainer --version  # Should show: apptainer version 1.x.x
python --version     # Should show: Python 3.12.3
```

---

## 4. Repository Setup

### Step 4.1: Clone the Repository

**Command**:
```bash
git clone https://github.com/Valegrl/Team6_EUMASTER4HPC2526.git
cd Team6_EUMASTER4HPC2526
```

**What this does**: Downloads the complete AI Factory Benchmarking Framework to your project directory.

**Repository contents**:
- `src/`: Framework source code (client, server, monitor, reporter, etc.)
- `recipe.yml`: Benchmark configuration file
- `scripts/`: Helper scripts for building and running benchmarks
- `apptainer_recipes/`: Container definitions for AI services
- `requirements.txt`: Python dependencies

### Step 4.2: Create Python Virtual Environment

**Commands**:
```bash
python -m venv venv
source venv/bin/activate
```

**What this does**:
- Creates an isolated Python environment in `venv/` directory
- Activates it (your prompt should now show `(venv)`)

**Why isolation matters**:
- Prevents dependency conflicts with system packages
- Allows specific package versions required by the framework
- Makes environment reproducible across different systems
- Easy to clean up (just delete `venv/` directory)

**Verification**:
```bash
which python  # Should show: .../Team6_EUMASTER4HPC2526/venv/bin/python
```

### Step 4.3: Install Python Dependencies

**Command**:
```bash
pip install -r requirements.txt
```

**What this installs**:
- `PyYAML`: For reading/parsing `recipe.yml` configuration
- `requests`: For making HTTP requests to services
- `sqlite3`: For storing metrics (usually built-in)
- Other dependencies for monitoring and reporting

**Why these packages**:
- **PyYAML**: The framework uses YAML for human-readable configuration
- **requests**: Core library for HTTP communication with AI services
- Each dependency supports a specific framework component

**Verification**:
```bash
pip list  # Should show all installed packages
python -c "import yaml, requests; print('Dependencies OK')"
```

---

## 5. Building Service Containers

### Understanding Container Need

**What are containers**: Packaged applications with all their dependencies, ready to run anywhere.

**Why Apptainer**: Unlike Docker, Apptainer:
- Works in HPC environments without root privileges
- Integrates seamlessly with SLURM
- Supports GPU passthrough for AI workloads
- Provides security features required for shared systems

### Step 5.1: Create Container Directory

**Command**:
```bash
mkdir -p containers
```

**What this does**: Creates a dedicated directory for storing built container images (.sif files).

**Why separate directory**: Keeps containers organized and easy to reference in scripts.

### Step 5.2: Build or Pull Containers

You have two options:

#### Option A: Build from Definition Files (Recommended for Customization)

**Command**:
```bash
bash scripts/build_containers.sh
```

**What this does**:
- Reads Apptainer definition files from `apptainer_recipes/`
- Builds container images for each service:
  - `ollama.sif`: Ollama LLM inference service
  - `vllm.sif`: vLLM high-performance inference
  - `chromadb.sif`: ChromaDB vector database
  - `postgres.sif`: PostgreSQL database
- Saves containers in `containers/` directory

**Time required**: 15-45 minutes depending on service complexity

**Why this option**: 
- Full control over container configuration
- Can customize service settings
- Optimized for MeluXina environment

#### Option B: Pull Pre-built Docker Images (Faster)

**Commands**:
```bash
cd containers
apptainer pull docker://ollama/ollama
apptainer pull docker://vllm/vllm-openai:latest
apptainer pull docker://chromadb/chroma:latest
apptainer pull docker://postgres:16
```

**What this does**: 
- Downloads pre-built containers from Docker Hub
- Converts them to Apptainer format (.sif)
- Ready to use immediately

**Time required**: 5-15 minutes depending on network speed

**Why this option**:
- Much faster than building
- Officially maintained images
- Good for quick testing

### Step 5.3: Verify Container Images

**Command**:
```bash
ls -lh containers/
```

**What to expect**: You should see .sif files like:
```
ollama_ollama.sif         # ~1-2 GB
vllm_vllm-openai_latest.sif  # ~3-5 GB
chromadb_chroma_latest.sif   # ~500 MB
postgres_16.sif          # ~300 MB
```

**Test a container**:
```bash
apptainer exec containers/ollama_ollama.sif ollama --version
```
Not working, maybe:
```bash
apptainer exec containers/ollama_latest.sif ollama serve
```

**What this does**: Runs a command inside the container to verify it works.

---

## 6. Configuring Your Benchmark

### Understanding recipe.yml

The `recipe.yml` file is the **single source of truth** for your benchmark configuration. It defines:
- Which services to benchmark
- How much load to generate
- How long to run
- Resource requirements for SLURM

### Step 6.1: Open the Configuration File

**Command**:
```bash
vim recipe.yml
# or use nano, emacs, or any editor you prefer
```

### Step 6.2: Understanding Configuration Sections

#### Global Settings

```yaml
benchmark:
  name: "AI Factory Services Benchmark"
  description: "Comprehensive benchmarking of AI services"
  duration: 300  # Total benchmark suite duration
```

**What this does**: Sets overall benchmark parameters and metadata.

#### Service Configuration Example

```yaml
services:
  - service_name: ollama-llama2
    service_type: ollama
    container_image: docker://ollama/ollama
    port: 11434
    client_count: 5
    requests_per_second: 10
    duration: 60
    service_url: http://localhost:11434
    slurm:
      partition: gpu
      account: p200981
      time: "01:00:00"
      nodes: 1
      ntasks: 1
      qos: default
    model: llama2
```

**Field-by-field explanation**:

- **service_name**: `ollama-llama2`
  - **What**: Unique identifier for this service in logs/reports
  - **Why**: Helps you distinguish between multiple services or configurations

- **service_type**: `ollama`
  - **What**: Type of AI service (ollama, vllm, vectordb, database)
  - **Why**: Determines how the client generates requests (each service has different APIs)

- **container_image**: `docker://ollama/ollama`
  - **What**: Source container for this service
  - **Why**: Specifies which container to run for this service

- **port**: `11434`
  - **What**: Network port where service listens
  - **Why**: Each service needs a unique port; client uses this to connect

- **client_count**: `5`
  - **What**: Number of concurrent client threads
  - **Why**: Simulates multiple users accessing the service simultaneously
  - **Impact**: More clients = higher load = better stress testing

- **requests_per_second**: `10`
  - **What**: Target request rate per client
  - **Why**: Controls the intensity of the benchmark
  - **Total load**: 5 clients × 10 RPS = 50 requests/second

- **duration**: `60`
  - **What**: How long to run this service's benchmark (in seconds)
  - **Why**: Longer duration gives more reliable statistics
  - **Expected requests**: 5 clients × 10 RPS × 60s = 3000 total requests

- **service_url**: `http://localhost:11434`
  - **What**: URL where the service is accessible
  - **Why**: Client needs to know where to send requests
  - **Note**: On MeluXina, service runs on same node as client (localhost)

- **slurm.partition**: `gpu`
  - **What**: SLURM partition to use (gpu or cpu)
  - **Why**: LLM services need GPU acceleration; databases can use CPU
  - **Options**: 
    - `gpu`: For Ollama, vLLM (AI inference)
    - `cpu`: For ChromaDB, PostgreSQL

- **slurm.account**: `p200981`
  - **What**: Your project allocation account
  - **Why**: Tracks resource usage for billing/quota
  - **Important**: **CHANGE THIS** to your actual project account

- **slurm.time**: `"01:00:00"`
  - **What**: Maximum job runtime (HH:MM:SS format)
  - **Why**: SLURM kills jobs exceeding this limit
  - **Guideline**: Set 20-30% higher than expected duration

- **slurm.nodes**: `1`
  - **What**: Number of compute nodes to allocate
  - **Why**: Each service typically runs on one node for this benchmark

- **slurm.qos**: `default`
  - **What**: Quality of Service level
  - **Why**: Affects job priority and resource limits
  - **Options**: Check your project's available QoS levels

- **model**: `llama2`
  - **What**: AI model to use (for LLM services)
  - **Why**: Different models have different performance characteristics
  - **Note**: Model must be available in the container or will be downloaded

### Step 6.3: Customize for Your Test

**For a quick test**, modify to:
```yaml
services:
  - service_name: ollama-test
    service_type: ollama
    container_image: docker://ollama/ollama
    port: 11434
    client_count: 2        # Fewer clients
    requests_per_second: 5  # Lower rate
    duration: 30           # Shorter duration
    service_url: http://localhost:11434
    slurm:
      partition: gpu
      account: YOUR_PROJECT_ACCOUNT  # ← CHANGE THIS!
      time: "00:30:00"
      nodes: 1
      ntasks: 1
      qos: default
    model: llama2
```

**Why these changes**:
- **Fewer clients/requests**: Faster completion, lower resource usage
- **Shorter duration**: Quick validation that everything works
- **Smaller time allocation**: Less queue wait, faster job start

**For production benchmarking**:
- Use higher client counts (10-20)
- Higher RPS (20-50 for LLMs, 100+ for databases)
- Longer duration (300-600 seconds) for statistical significance
- Test multiple services simultaneously

### Step 6.4: Validate Configuration

**Command**:
```bash
python -c "import yaml; yaml.safe_load(open('recipe.yml'))"
```

**What this does**: Checks if your YAML syntax is correct.

**If error**: Review the error message, common issues:
- Incorrect indentation (YAML is whitespace-sensitive)
- Missing quotes around strings with special characters
- Mismatched brackets or colons

---

## 7. Validating the Environment

### Step 7.1: Run Validation Script

**Command**:
```bash
bash scripts/validate_meluxina.sh
```

**What this does**: Performs comprehensive environment checks:

1. **Python Version Check**
   - Verifies Python 3.8+ is available
   - Why: Framework requires modern Python features

2. **Apptainer Check**
   - Confirms Apptainer/Singularity is installed
   - Why: Required to run service containers

3. **SLURM Check**
   - Verifies SLURM commands are accessible
   - Why: Needed for job submission and management

4. **Python Dependencies Check**
   - Tests if required packages are installed
   - Why: Framework won't run without them

5. **Directory Structure Check**
   - Confirms all required directories exist
   - Why: Framework expects specific structure

6. **Required Files Check**
   - Verifies critical files are present
   - Why: Missing files cause runtime errors

7. **Storage Paths Check**
   - Validates PROJECT environment variable
   - Why: Ensures you're in the right location

8. **GPU Availability Check** (optional)
   - Detects available GPUs
   - Why: Important for LLM benchmarking

9. **Framework Import Test**
   - Tests if Python can import all components
   - Why: Catches missing dependencies or code issues

10. **Write Permissions Check**
    - Verifies you can write to logs/ and reports/
    - Why: Framework needs to save results

### Step 7.2: Interpret Results

**Expected output**:
```
============================================================
VALIDATION SUMMARY
============================================================
✓ Passed: 20
✗ Failed: 0

✓ Environment is ready for benchmarking!
```

**If checks fail**:
- Read the specific failure message
- Common fixes:
  ```bash
  # If Python dependencies missing:
  pip install -r requirements.txt
  
  # If modules not loaded:
  module add Apptainer
  module load Python/3.12.3-GCCcore-13.3.0
  
  # If directories missing:
  mkdir -p logs reports containers
  ```

---

## 8. Running Your First Test Benchmark

### Understanding Test vs Production

**Test run**: Quick validation that everything works
- Short duration (30-60 seconds)
- Low load (2-5 clients, low RPS)
- Single service
- Purpose: Verify setup before committing to long runs

**Production run**: Full-scale benchmarking
- Long duration (300-600 seconds)
- High load (10-20+ clients, high RPS)
- Multiple services
- Purpose: Gather meaningful performance data

### Step 8.1: Local Test (Optional but Recommended)

**Command**:
```bash
bash scripts/test_local.sh
```

**What this does**:
1. Creates necessary directories (logs, reports)
2. Sets up Python virtual environment if needed
3. Installs dependencies
4. Runs the benchmark framework locally (without SLURM)

**Why run locally first**:
- No queue wait time
- Immediate feedback
- Catches configuration errors quickly
- Doesn't consume HPC allocation

**Expected output**:
```
======================================
AI Factory Benchmarking Framework
Local Test Run
======================================
Installing dependencies...
Starting benchmark...
Step 1: Initializing middleware...
Step 2: Starting services...
Step 3: Setting up monitoring...
Step 4: Running benchmarks...
...
```

**Limitations of local test**:
- Services run on login node (limited resources)
- No GPU access
- May timeout for large services
- Not suitable for real measurements

**When it's useful**:
- Validating recipe.yml syntax
- Testing framework code changes
- Quick smoke tests

### Step 8.2: Submit Interactive Job (Recommended for First Real Test)

**Command**:
```bash
salloc --partition=gpu --account=p200981 --qos=default \
       --time=00:30:00 --nodes=1
```

**What this does**:
- Requests an interactive session on a compute node
- Gives you a shell on the allocated node
- Waits in queue until resources available

**Why interactive for first test**:
- Real-time feedback
- Can observe execution directly
- Easy to stop if something goes wrong
- Can inspect environment interactively

**Once allocated** (prompt changes to show compute node):
```bash
# Confirm you're on compute node
hostname  # Should show: mel-XXXX (not login node)

# Load modules again (compute node environment)
module add Apptainer
module load Python/3.12.3-GCCcore-13.3.0

# Activate virtual environment
cd /path/to/Team6_EUMASTER4HPC2526
source venv/bin/activate

# Run benchmark
python src/main.py --recipe recipe.yml
```

**What happens during execution**:

1. **Initialization** (5-10 seconds)
   ```
   Step 1: Initializing middleware...
   Initializing middleware interface...
   ```
   - Loads configuration from recipe.yml
   - Sets up logging
   - Initializes framework components

2. **Service Startup** (30-120 seconds)
   ```
   Step 2: Starting services...
   Starting service: ollama-llama2
   ```
   - Launches Apptainer container
   - Starts AI service inside container
   - Waits for service to become ready
   - **Note**: First time may download model (can take minutes)

3. **Monitoring Setup** (5 seconds)
   ```
   Step 3: Setting up monitoring...
   Initializing monitor...
   ```
   - Creates SQLite database (metrics.db)
   - Sets up metrics collection
   - Prepares logging infrastructure

4. **Benchmark Execution** (depends on duration setting)
   ```
   Step 4: Running benchmarks...
   Benchmarking service: ollama-llama2
     Client count: 5
     Requests per second: 10
     Duration: 60s
     Starting real benchmark execution...
   ```
   - Spawns client threads
   - Sends HTTP requests to service
   - Measures response times
   - Captures success/failure rates
   - Records all metrics
   
   **What you'll see**:
   - Progress indicators
   - Request counts
   - Any errors (logged immediately)

5. **Completion** (when duration ends)
   ```
     Completed 3000 requests
   Successfully benchmarked: ollama-llama2
   ```

6. **Report Generation** (10-30 seconds)
   ```
   Step 5: Generating reports...
   Report saved to: reports/benchmark_1234567890_report.json
   ```
   - Aggregates all metrics
   - Calculates statistics
   - Generates JSON report

7. **Cleanup**
   ```
   Step 6: Cleanup...
   Benchmark workflow completed!
   ```
   - Stops services
   - Releases resources
   - Finalizes logs

**Monitoring during execution**:

Open another terminal and SSH to MeluXina:
```bash
# Watch queue status
watch squeue -u $USER

# Tail logs in real-time
tail -f logs/benchmark_*.log

# Check metrics database
sqlite3 metrics.db "SELECT COUNT(*) FROM metrics;"
```

### Step 8.3: Exit Interactive Session

**Command**:
```bash
exit  # or Ctrl+D
```

**What this does**: Releases the compute node allocation back to SLURM.

---

## 9. Submitting Full-Scale Benchmarks

Once you've validated the setup with a test, you can submit batch jobs for unattended execution.

### Step 9.1: Understand Batch Job Workflow

**Batch jobs**:
- Submit and disconnect
- Run unattended on compute nodes
- No need to stay logged in
- Output saved to files

**Workflow**:
```
You submit → Job queues → Resources allocated → Job runs → Results saved
    ↓            ↓              ↓                  ↓            ↓
  sbatch       PENDING        RUNNING          COMPLETING   COMPLETED
```

### Step 9.2: Review Batch Script

**Command**:
```bash
cat scripts/run_benchmark.sh
```

**Key sections explained**:

```bash
#SBATCH --job-name=ai_factory_benchmark
```
- **What**: Name appearing in queue
- **Why**: Helps identify your jobs

```bash
#SBATCH --time=02:00:00
```
- **What**: Maximum runtime (2 hours)
- **Why**: Job killed if exceeds this
- **Guideline**: Set 20-30% above expected duration

```bash
#SBATCH --partition=gpu
```
- **What**: Which partition to use
- **Why**: GPU needed for LLM services
- **Change to**: `cpu` if only benchmarking databases

```bash
#SBATCH --account=p200981
```
- **What**: Project account for resource tracking
- **Why**: Required for all jobs
- **Important**: Change to YOUR account

```bash
#SBATCH --output=logs/benchmark_%j.out
#SBATCH --error=logs/benchmark_%j.err
```
- **What**: Where stdout/stderr are saved
- **Why**: Captures all job output for review
- **%j**: Replaced with job ID automatically

**Script execution flow**:
1. Prints job information
2. Loads required modules
3. Creates directories
4. Sets up Python environment
5. Runs the benchmark
6. Prints completion message

### Step 9.3: Submit Batch Job

**Command**:
```bash
sbatch scripts/run_benchmark.sh
```

**Output**:
```
Submitted batch job 1234567
```

**What this means**: 
- Job accepted by SLURM
- Assigned job ID 1234567
- Now in queue waiting for resources

### Step 9.4: Customize Batch Submission (Advanced)

You can override parameters at submission:

```bash
# Different account
sbatch --account=p200999 scripts/run_benchmark.sh

# Different time limit
sbatch --time=03:00:00 scripts/run_benchmark.sh

# Different partition
sbatch --partition=cpu scripts/run_benchmark.sh

# Multiple overrides
sbatch --account=p200999 --time=03:00:00 --partition=gpu \
       scripts/run_benchmark.sh
```

**Why override**: Test different configurations without editing the script.

### Step 9.5: Submit Multiple Services

To benchmark multiple services in parallel:

**Option A: Multiple jobs**
```bash
# Submit separate jobs for each service
sbatch scripts/slurm/ollama-llama2_service.sh
sbatch scripts/slurm/vllm-inference_service.sh
sbatch scripts/slurm/chromadb_service.sh
```

**What this does**: Each service gets its own compute node and runs independently.

**Why**: 
- Services don't interfere with each other
- Different resource requirements (GPU vs CPU)
- Can run simultaneously if resources available

**Option B: Comprehensive benchmark**
```bash
# Edit recipe.yml to include all services, then:
sbatch scripts/run_benchmark.sh
```

**What this does**: All services in recipe.yml are benchmarked sequentially.

**Why**:
- Single job, easier to manage
- Consistent environment
- Serialized execution ensures no resource conflicts

---

## 10. Monitoring Execution

### Step 10.1: Check Job Status

**Command**:
```bash
squeue -u $USER
```

**Output explanation**:
```
JOBID   PARTITION  NAME                  USER    ST  TIME  NODES
1234567 gpu        ai_factory_benchmark  youruser PD  0:00  1
```

**Status codes**:
- **PD** (Pending): Waiting for resources
  - **Reason**: Type `squeue -u $USER --start` to see when it might start
  - **Common reasons**: Queue busy, higher priority jobs, resource unavailable

- **R** (Running): Currently executing
  - **Monitor**: Check logs, metrics, etc.

- **CG** (Completing): Finishing up, cleaning resources

- **CD** (Completed): Successfully finished
  - **Next step**: Review results

- **F** (Failed): Job failed
  - **Action**: Check error logs

- **CA** (Cancelled): User or admin cancelled
  - **Why**: Manual cancellation or policy violation

**Detailed job info**:
```bash
scontrol show job 1234567
```

**What this shows**:
- Exact start time
- Resource allocation
- Working directory
- Failure reasons (if failed)
- Much more detailed information

### Step 10.2: Monitor Job Output in Real-Time

**While job is running**:

```bash
# Watch standard output
tail -f logs/benchmark_1234567.out

# Watch error output
tail -f logs/benchmark_1234567.err

# Watch both
tail -f logs/benchmark_1234567.{out,err}
```

**What you see**:
- Framework progress messages
- Service startup logs
- Request execution logs
- Metrics collection updates
- Any errors or warnings

**Ctrl+C to stop watching** (job continues running)

### Step 10.3: Check Application Logs

**Command**:
```bash
# List all benchmark logs
ls -lt logs/*.log | head

# View latest log
tail -f logs/benchmark_*.log
```

**What's in application logs**:
- Timestamp for each operation
- Component-level details
- Service health status
- Request/response details
- Error stack traces

### Step 10.4: Monitor Metrics Database

**Commands**:
```bash
# Connect to metrics database
sqlite3 metrics.db

# Inside sqlite3:
.tables                     # List tables
SELECT COUNT(*) FROM metrics;  # Count total metrics
SELECT * FROM metrics LIMIT 5; # View sample metrics
.exit                       # Exit sqlite3
```

**What this shows**: Real-time accumulation of metrics during benchmark execution.

**Why useful**: Confirm data is being collected correctly while job runs.

### Step 10.5: Check Resource Usage

**Command**:
```bash
sacct -j 1234567 --format=JobID,JobName,Partition,State,Elapsed,MaxRSS,AveCPU
```

**What this shows**:
- **MaxRSS**: Maximum memory used
- **AveCPU**: Average CPU utilization
- **Elapsed**: Actual runtime

**Why important**:
- Verify you're not over/under allocating resources
- Optimize future job submissions
- Understand performance characteristics

### Step 10.6: Cancel a Job (if needed)

**Command**:
```bash
scancel 1234567
```

**When to cancel**:
- Job is stuck or not progressing
- Configuration error discovered
- Need to free resources urgently

**What happens**:
- Job receives SIGTERM (graceful shutdown request)
- After 30 seconds, receives SIGKILL (forced termination)
- Partial results may be saved

---

## 11. Analyzing Results

### Step 11.1: Locate Result Files

**Command**:
```bash
ls -lh reports/
ls -lh logs/
ls -lh metrics.db
```

**Expected files**:
```
reports/benchmark_1234567890_report.json  # Main report
logs/benchmark_1234567890.log             # Detailed log
logs/benchmark_1234567.out                # SLURM stdout
logs/benchmark_1234567.err                # SLURM stderr
metrics.db                                 # Raw metrics
```

### Step 11.2: View Report Summary

**Command**:
```bash
cat reports/benchmark_*_report.json | python -m json.tool | less
```

**What this does**:
- Reads the JSON report
- Formats it for easy reading
- Displays in paginated viewer (less)

**Report structure**:

```json
{
  "benchmark_id": "benchmark_1234567890",
  "timestamp": "2025-10-22T10:30:00",
  "summary": {
    "total_requests": 3000,
    "successful_requests": 2950,
    "failed_requests": 50,
    "success_rate": 98.33,
    "total_duration": 60.5
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
    "ollama-llama2": {
      "total_requests": 3000,
      "success_rate": 98.33,
      "throughput": 49.59,
      "timing": {...},
      "errors": [...]
    }
  }
}
```

**Key metrics explained**:

- **total_requests**: Total requests sent during benchmark
  - **Calculation**: client_count × requests_per_second × duration
  - **Verify**: Should match expected value

- **success_rate**: Percentage of successful requests
  - **Good**: > 95% (some failures normal under high load)
  - **Concerning**: < 90% (may indicate service issues)
  - **Bad**: < 50% (serious problems)

- **avg_duration**: Average response time in seconds
  - **Compare**: Against service SLAs or baselines
  - **Note**: Lower is better
  - **Context**: Varies by service type (LLMs slower than DB queries)

- **percentiles**: Distribution of response times
  - **p50 (median)**: Half of requests faster, half slower
  - **p90**: 90% of requests faster than this
  - **p95**: 95% of requests faster than this
  - **p99**: 99% of requests faster than this
  - **Why important**: Reveals outliers and tail latencies

- **throughput**: Actual requests per second achieved
  - **Compare**: Against target RPS
  - **If lower**: Service couldn't keep up with load
  - **If higher**: Good! Service handled load well

### Step 11.3: Analyze Individual Service Performance

**Extract service-specific data**:
```bash
python -c "
import json
with open('reports/benchmark_*_report.json') as f:
    data = json.load(f)
    for service, metrics in data['services'].items():
        print(f'\n{service}:')
        print(f'  Success Rate: {metrics["success_rate"]}%')
        print(f'  Throughput: {metrics["throughput"]} RPS')
        print(f'  Avg Latency: {metrics["timing"]["avg_duration"]}s')
"
```

### Step 11.4: Compare Multiple Benchmarks

**List all reports**:
```bash
for report in reports/*.json; do
    echo "=== $(basename $report) ==="
    python -c "
import json
with open('$report') as f:
    data = json.load(f)
    print(f'Success Rate: {data["summary"]["success_rate"]}%')
    print(f'Avg Latency: {data["timing"]["avg_duration"]}s')
    print(f'Throughput: {data["summary"]["total_requests"] / data["summary"]["total_duration"]:.2f} RPS')
    "
    echo ""
done
```

**What this does**: Prints key metrics from all reports for easy comparison.

**Use cases**:
- Compare different service types (Ollama vs vLLM)
- Evaluate impact of configuration changes
- Identify performance trends over time
- Validate optimization efforts

### Step 11.5: Investigate Errors

**Command**:
```bash
grep -i error logs/benchmark_*.log
```

**Common error types**:

1. **Connection Refused**
   ```
   Error: Connection refused to http://localhost:11434
   ```
   - **Meaning**: Service not running or not ready
   - **Fix**: Increase service startup wait time

2. **Timeout**
   ```
   Error: Request timeout after 30s
   ```
   - **Meaning**: Service too slow or overloaded
   - **Fix**: Reduce RPS or increase timeout

3. **500 Internal Server Error**
   ```
   Error: HTTP 500 Internal Server Error
   ```
   - **Meaning**: Service crashed or encountered error
   - **Fix**: Check service logs, reduce load

4. **Out of Memory**
   ```
   Error: OOM killed
   ```
   - **Meaning**: Service exhausted available memory
   - **Fix**: Request more memory in SLURM or use smaller model

### Step 11.6: Query Metrics Database Directly

**Commands**:
```bash
sqlite3 metrics.db << EOF
-- Summary statistics
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
    AVG(request_duration) as avg_duration,
    MIN(request_duration) as min_duration,
    MAX(request_duration) as max_duration
FROM metrics
WHERE benchmark_id = 'benchmark_1234567890';

-- Requests by client
SELECT 
    client_id,
    COUNT(*) as requests,
    AVG(request_duration) as avg_duration
FROM metrics
WHERE benchmark_id = 'benchmark_1234567890'
GROUP BY client_id;

-- Error distribution
SELECT 
    status_code,
    COUNT(*) as count
FROM metrics
WHERE benchmark_id = 'benchmark_1234567890'
  AND success = 0
GROUP BY status_code;
EOF
```

**Why query directly**: 
- Custom analysis not in standard reports
- Troubleshooting specific issues
- Export data for external tools

---

## 12. Exporting Metrics

### Step 12.1: Export to Prometheus Format

**Command**:
```bash
python src/monitoring/prometheus_exporter.py benchmark_1234567890
```

**What this does**: 
- Reads metrics from metrics.db
- Converts to Prometheus exposition format
- Outputs to stdout

**Output example**:
```
# HELP benchmark_requests_total Total number of requests
# TYPE benchmark_requests_total counter
benchmark_requests_total{service="ollama-llama2"} 3000

# HELP benchmark_request_duration_seconds Request duration in seconds
# TYPE benchmark_request_duration_seconds histogram
benchmark_request_duration_seconds_bucket{le="0.5",service="ollama-llama2"} 1500
benchmark_request_duration_seconds_bucket{le="1.0",service="ollama-llama2"} 2800
benchmark_request_duration_seconds_bucket{le="+Inf",service="ollama-llama2"} 3000
```

### Step 12.2: Save to File

**Command**:
```bash
python src/monitoring/prometheus_exporter.py benchmark_1234567890 \
    -o metrics.prom
```

**What this does**: Saves metrics to `metrics.prom` file.

**Why**: 
- Can be scraped by Prometheus
- Pushed to Pushgateway
- Imported into monitoring systems

### Step 12.3: Push to Prometheus Pushgateway (if configured)

**Command**:
```bash
python src/monitoring/prometheus_exporter.py benchmark_1234567890 \
    --push --gateway http://prometheus-pushgateway:9091
```

**What this does**: Pushes metrics directly to Prometheus Pushgateway.

**Why useful**:
- Real-time monitoring in Grafana
- Alert on performance regressions
- Historical trend analysis

### Step 12.4: Export to CSV (for Excel/Analysis)

**Command**:
```bash
sqlite3 -header -csv metrics.db \
    "SELECT * FROM metrics WHERE benchmark_id = 'benchmark_1234567890'" \
    > metrics.csv
```

**What this does**: Exports raw metrics to CSV format.

**Use cases**:
- Import into Excel for custom analysis
- Statistical analysis in R or Python
- Share data with stakeholders
- Archive for long-term storage

---

## 13. Troubleshooting Common Issues

### Issue 1: Job Stays in Pending (PD) State

**Symptoms**: Job doesn't start after submission.

**Check reason**:
```bash
squeue -u $USER --start
```

**Common reasons and fixes**:

- **Resources**: Partition busy or insufficient resources
  ```bash
  # Check partition status
  sinfo -p gpu
  
  # Fix: Try different partition or wait
  sbatch --partition=cpu scripts/run_benchmark.sh
  ```

- **Priority**: Other jobs have higher priority
  ```bash
  # Check your priority
  sprio -u $USER
  
  # Fix: Wait, or contact admin for priority increase
  ```

- **QoS**: Quality of Service restrictions
  ```bash
  # Check QoS limits
  sacctmgr show qos
  
  # Fix: Use different QoS
  sbatch --qos=short scripts/run_benchmark.sh
  ```

- **Reservation**: Resources reserved for other users
  ```bash
  # Check reservations
  scontrol show reservation
  
  # Fix: Wait for reservation to end
  ```

### Issue 2: Job Fails Immediately

**Symptoms**: Job goes from PD to F (Failed) quickly.

**Check logs**:
```bash
cat logs/benchmark_1234567.err
```

**Common causes**:

- **Module not found**
  ```
  Error: module: command not found
  ```
  Fix:
  ```bash
  # Add to script or run manually:
  . /etc/profile.d/modules.sh
  module add Apptainer
  module load Python
  ```

- **File not found**
  ```
  Error: recipe.yml: No such file or directory
  ```
  Fix: Ensure working directory is correct in SLURM script:
  ```bash
  #SBATCH --chdir=/path/to/Team6_EUMASTER4HPC2526
  ```

- **Permission denied**
  ```
  Error: Permission denied: 'logs/benchmark.log'
  ```
  Fix:
  ```bash
  chmod +x scripts/*.sh
  mkdir -p logs reports
  chmod u+w logs reports
  ```

### Issue 3: Service Fails to Start

**Symptoms**: Benchmark reports service unavailable.

**Check service logs**:
```bash
grep -A 10 "Starting service" logs/benchmark_*.log
```

**Common issues**:

- **Container not found**
  ```
  Error: Unable to find container: ollama_ollama.sif
  ```
  Fix:
  ```bash
  # Build or pull container
  cd containers
  apptainer pull docker://ollama/ollama
  ```

- **Port already in use**
  ```
  Error: Address already in use: 11434
  ```
  Fix: Change port in recipe.yml or kill existing process:
  ```bash
  lsof -ti :11434 | xargs kill -9
  ```

- **GPU not available**
  ```
  Error: No GPU devices found
  ```
  Fix:
  ```bash
  # Verify GPU partition
  sbatch --partition=gpu --gres=gpu:1 scripts/run_benchmark.sh
  ```

### Issue 4: High Failure Rate

**Symptoms**: Success rate < 80%.

**Investigate**:
```bash
# Check error types
sqlite3 metrics.db "
SELECT status_code, error, COUNT(*) 
FROM metrics 
WHERE success = 0 
GROUP BY status_code, error;
"
```

**Common causes**:

- **Service overloaded**
  - **Symptoms**: Lots of timeouts or 503 errors
  - **Fix**: Reduce RPS or client_count in recipe.yml

- **Model not loaded**
  - **Symptoms**: 404 errors for Ollama/vLLM
  - **Fix**: Pre-pull model or increase startup wait time

- **Network issues**
  - **Symptoms**: Connection refused or resets
  - **Fix**: Check service logs, verify networking

### Issue 5: Out of Memory (OOM)

**Symptoms**: Job killed with OOM message.

**Check**:
```bash
sacct -j 1234567 --format=JobID,MaxRSS,ReqMem
```

**Solutions**:

- **Request more memory**
  ```bash
  sbatch --mem=64G scripts/run_benchmark.sh
  ```

- **Use smaller model**
  ```yaml
  # In recipe.yml:
  model: llama2:7b  # Instead of llama2:13b
  ```

- **Reduce concurrency**
  ```yaml
  # In recipe.yml:
  client_count: 3  # Instead of 10
  ```

### Issue 6: Metrics Database Locked

**Symptoms**: 
```
Error: database is locked
```

**Causes**: 
- Multiple processes accessing SQLite simultaneously
- Unclean shutdown left lock file

**Fix**:
```bash
# Check for lock file
ls -la metrics.db-*

# Remove if safe
rm metrics.db-journal metrics.db-wal

# Or use different database per run
# In recipe.yml:
global:
  metrics_db: metrics_${SLURM_JOB_ID}.db
```

### Issue 7: Python Import Errors

**Symptoms**:
```
ModuleNotFoundError: No module named 'yaml'
```

**Fixes**:

```bash
# Ensure virtual environment is activated
source venv/bin/activate
which python  # Should show venv path

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# If still fails, try system-wide (not recommended)
pip install --user -r requirements.txt
```

### Issue 8: Container Build Fails

**Symptoms**: Apptainer build errors.

**Common issues**:

- **Insufficient space**
  ```
  Error: No space left on device
  ```
  Fix:
  ```bash
  # Check space
  df -h $HOME
  
  # Use project directory for cache
  export APPTAINER_CACHEDIR=$PROJECT/apptainer_cache
  mkdir -p $APPTAINER_CACHEDIR
  ```

- **Network timeout**
  ```
  Error: Timeout while fetching image
  ```
  Fix:
  ```bash
  # Retry with increased timeout
  apptainer build --timeout 3600 ollama.sif docker://ollama/ollama
  ```

- **Architecture mismatch**
  ```
  Error: exec format error
  ```
  Fix: Ensure container matches MeluXina architecture (x86_64)

### Getting Additional Help

**Resources**:
1. **MeluXina Documentation**: https://docs.lxp.lu/
2. **Project Issues**: https://github.com/Valegrl/Team6_EUMASTER4HPC2526/issues
3. **SLURM Documentation**: https://slurm.schedmd.com/
4. **Apptainer Documentation**: https://apptainer.org/docs/

**Support Channels**:
- MeluXina Support: support@lxp.lu
- Project GitHub: Create an issue with:
  - Error messages
  - Log files
  - Configuration used
  - Steps to reproduce

---

## 14. Advanced Configuration

### 14.1: Benchmarking Multiple Services Simultaneously

**Edit recipe.yml**:
```yaml
services:
  # LLM Service on GPU
  - service_name: ollama-llama2
    service_type: ollama
    port: 11434
    client_count: 5
    requests_per_second: 10
    duration: 300
    slurm:
      partition: gpu
      account: p200981
      
  # Vector DB on CPU
  - service_name: chromadb
    service_type: vectordb
    port: 8001
    client_count: 10
    requests_per_second: 50
    duration: 300
    slurm:
      partition: cpu
      account: p200981
```

**What happens**: Framework benchmarks each service sequentially.

**Why sequential**: Avoids resource conflicts and ensures clean metrics.

### 14.2: Custom Service Commands

For services needing special startup:

**Create custom SLURM script**:
```bash
#!/bin/bash
#SBATCH --job-name=custom-service
#SBATCH --partition=gpu
#SBATCH --account=p200981
#SBATCH --time=01:00:00

# Load modules
module add Apptainer

# Custom environment
export CUSTOM_VAR=value

# Start service with custom command
apptainer exec --nv \
    --bind /data:/data \
    --env CUSTOM_VAR=$CUSTOM_VAR \
    containers/custom.sif \
    custom-service --port 8080 --gpu
```

### 14.3: Multi-Node Benchmarking

For distributed services:

**SLURM script modifications**:
```bash
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=1

# Get list of allocated nodes
NODES=$(scontrol show hostname $SLURM_JOB_NODELIST)

# Start service on each node
for node in $NODES; do
    srun --nodes=1 --nodelist=$node \
        apptainer exec containers/service.sif service-start &
done

wait  # Wait for all to start

# Run benchmark
python src/main.py --recipe recipe.yml
```

### 14.4: GPU-Specific Configuration

**For multi-GPU benchmarking**:
```yaml
slurm:
  partition: gpu
  gres: gpu:4  # Request 4 GPUs
  ntasks: 4    # One task per GPU
```

**In container launch**:
```bash
# Use specific GPU
CUDA_VISIBLE_DEVICES=0 apptainer exec --nv ...

# Or use all GPUs
apptainer exec --nv ...
```

### 14.5: Custom Metrics Collection

**Extend interceptor** (`src/interceptor/interceptor.py`):
```python
@dataclass
class MetricData:
    # Standard fields
    timestamp: float
    duration: float
    success: bool
    
    # Add custom fields
    gpu_memory_used: int = None
    tokens_per_second: float = None
    model_load_time: float = None
```

**Why**: Capture service-specific performance metrics.

### 14.6: Automated Benchmark Suites

**Create wrapper script** (`scripts/run_suite.sh`):
```bash
#!/bin/bash
# Run comprehensive benchmark suite

CONFIGS=("config_small.yml" "config_medium.yml" "config_large.yml")

for config in "${CONFIGS[@]}"; do
    echo "Running benchmark with $config"
    sbatch --job-name="suite_$(basename $config)" \
           scripts/run_benchmark.sh $config
    sleep 10  # Stagger submissions
done
```

**What this does**: Submits multiple benchmark configurations automatically.

---

## 15. Best Practices

### 15.1: Resource Management

**Do's**:
- ✅ Request only resources you need
- ✅ Use appropriate partition (GPU vs CPU)
- ✅ Set realistic time limits
- ✅ Clean up old logs and reports regularly
- ✅ Monitor your allocation usage

**Don'ts**:
- ❌ Don't run on login nodes (use compute nodes)
- ❌ Don't request excessive resources "just in case"
- ❌ Don't leave services running after benchmarks
- ❌ Don't exceed your project allocation

**Check allocation usage**:
```bash
sacct -S 2025-10-01 --format=JobID,JobName,Elapsed,TotalCPU,State
```

### 15.2: Benchmarking Methodology

**For reliable results**:

1. **Warm-up period**: Run short test first to warm caches
   ```yaml
   duration: 30  # Warm-up
   # Then run main benchmark
   duration: 300
   ```

2. **Multiple runs**: Run benchmark 3-5 times, average results
   ```bash
   for i in {1..3}; do
       sbatch --job-name="run_$i" scripts/run_benchmark.sh
   done
   ```

3. **Control variables**: Change one thing at a time
   - Keep load constant when comparing services
   - Keep service constant when testing different loads

4. **Statistical significance**: Longer duration = better statistics
   ```yaml
   duration: 600  # 10 minutes for reliable percentiles
   ```

### 15.3: Configuration Management

**Version control**:
```bash
# Track recipe changes
git add recipe.yml
git commit -m "Benchmark config for Ollama vs vLLM comparison"
git tag benchmark-v1.0
```

**Configuration templates**:
```bash
# Create templates for common scenarios
cp recipe.yml recipes/recipe_llm_light.yml
cp recipe.yml recipes/recipe_llm_heavy.yml
cp recipe.yml recipes/recipe_vectordb.yml
```

### 15.4: Data Management

**Organize results**:
```bash
# Create dated directories
mkdir -p results/2025-10-22
mv reports/*.json results/2025-10-22/
mv logs/*.log results/2025-10-22/
```

**Archive old data**:
```bash
# Compress old results
tar -czf results_2025-10.tar.gz results/2025-10-*
rm -rf results/2025-10-*
```

**Backup metrics database**:
```bash
# Regular backups
cp metrics.db metrics_backup_$(date +%Y%m%d).db
```

### 15.5: Documentation

**Document your runs**:
```bash
# Create README for each major benchmark
cat > results/2025-10-22/README.md << EOF
# Ollama vs vLLM Performance Comparison

## Objective
Compare Ollama and vLLM inference performance with Llama2-7B model

## Configuration
- Client count: 10
- RPS: 20
- Duration: 300s

## Results Summary
- Ollama: 95% success, 0.8s avg latency
- vLLM: 98% success, 0.5s avg latency

## Conclusions
vLLM shows better performance and stability
EOF
```

### 15.6: Collaboration

**Sharing results with team**:
```bash
# Make results readable by group
chmod -R g+r results/
```

**Document changes**:
```bash
# Keep changelog
echo "$(date): Updated recipe for larger model test" >> CHANGELOG.md
```

### 15.7: Continuous Improvement

**Performance tracking**:
```bash
# Extract key metrics over time
for report in results/*/benchmark_*_report.json; do
    date=$(basename $(dirname $report))
    success=$(jq -r '.summary.success_rate' $report)
    latency=$(jq -r '.timing.avg_duration' $report)
    echo "$date,$success,$latency"
done > performance_trend.csv
```

**Regression detection**:
```bash
# Compare with baseline
baseline_latency=$(jq -r '.timing.avg_duration' baseline_report.json)
current_latency=$(jq -r '.timing.avg_duration' current_report.json)

if (( $(echo "$current_latency > $baseline_latency * 1.1" | bc -l) )); then
    echo "Warning: Performance regression detected!"
fi
```

---

## Summary Checklist

Complete workflow checklist:

- [ ] **Setup Phase**
  - [ ] Connect to MeluXina
  - [ ] Load required modules
  - [ ] Clone repository
  - [ ] Create Python virtual environment
  - [ ] Install dependencies

- [ ] **Preparation Phase**
  - [ ] Build or pull service containers
  - [ ] Configure recipe.yml
  - [ ] Update SLURM account to your project
  - [ ] Run validation script
  - [ ] Fix any validation errors

- [ ] **Testing Phase**
  - [ ] Run local test (optional)
  - [ ] Submit interactive job
  - [ ] Verify services start correctly
  - [ ] Confirm metrics collection works

- [ ] **Production Phase**
  - [ ] Configure full-scale benchmark
  - [ ] Submit batch job
  - [ ] Monitor job progress
  - [ ] Wait for completion

- [ ] **Analysis Phase**
  - [ ] Review job output logs
  - [ ] Analyze performance reports
  - [ ] Query metrics database
  - [ ] Export metrics if needed

- [ ] **Documentation Phase**
  - [ ] Document results
  - [ ] Archive important data
  - [ ] Share findings with team
  - [ ] Update configurations based on learnings

---

## Quick Reference Commands

**Essential commands you'll use frequently**:

```bash
# Setup
module add Apptainer
module load Python/3.12.3-GCCcore-13.3.0
source venv/bin/activate

# Validation
bash scripts/validate_meluxina.sh

# Container management
apptainer pull docker://ollama/ollama
ls -lh containers/

# Job submission
sbatch scripts/run_benchmark.sh
sbatch --account=YOUR_ACCOUNT scripts/run_benchmark.sh

# Monitoring
squeue -u $USER
tail -f logs/benchmark_*.out
tail -f logs/benchmark_*.log

# Job control
scancel JOBID

# Results
ls -lt reports/
cat reports/benchmark_*_report.json | python -m json.tool | less

# Cleanup
rm logs/old_*.log
tar -czf old_results.tar.gz reports/*.json
```

---

## Conclusion

You now have a complete guide to running real benchmarks on MeluXina. The framework executes **actual HTTP requests**, measures **real performance metrics**, and provides **reliable data** for optimizing AI Factory services.

**Remember**:
- Start with small tests before full-scale benchmarks
- Monitor your resource usage
- Document your configurations and results
- Iterate and improve based on findings

**For additional help**:
- See other documentation files in the repository
- Check GitHub issues for known problems
- Contact MeluXina support for infrastructure questions
- Review SLURM and Apptainer documentation for advanced usage

**Happy benchmarking!** 🚀
