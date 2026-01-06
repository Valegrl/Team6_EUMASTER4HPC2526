#!/usr/bin/env python3
"""
Server Component
Manages services running in Apptainer containers via Slurm
"""

import os
import subprocess
import logging
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages lifecycle of services running in Apptainer containers"""
    
    def __init__(self, service_config: Dict[str, Any]):
        """
        Initialize service manager
        
        Args:
            service_config: Service configuration from recipe
        """
        self.service_name = service_config.get('service_name')
        self.container_image = service_config.get('container_image')
        self.service_type = service_config.get('service_type', 'inference')
        self.port = service_config.get('port', 11434)
        self.model = service_config.get('model', 'facebook/opt-125m')
        self.backend = service_config.get('backend')  # For vectordb, database types
        self.slurm_config = service_config.get('slurm', {})
        self.job_id = None
        
    def start_service(self) -> bool:
        """
        Start the service via Slurm
        
        Returns:
            True if service started successfully
        """
        logger.info(f"Starting service: {self.service_name}")
        
        # Generate the Slurm batch script
        script_path = self._generate_slurm_script()
        
        logger.info(f"Service {self.service_name} configured with script: {script_path}")
        logger.info(f"Container image: {self.container_image}")
        logger.info(f"Port: {self.port}")
        
        # Submit the job to Slurm
        try:
            logger.info(f"Submitting job to Slurm: sbatch {script_path}")
            result = subprocess.run(
                ['sbatch', script_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse the job ID from sbatch output
            # Expected format: "Submitted batch job 12345"
            output = result.stdout.strip()
            logger.info(f"Slurm response: {output}")
            
            if "Submitted batch job" in output:
                self.job_id = output.split()[-1]
                logger.info(f"✓ Service submitted successfully with job ID: {self.job_id}")
                return True
            else:
                logger.error(f"Unexpected sbatch output: {output}")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to submit Slurm job: {e.stderr}")
            return False
        except FileNotFoundError:
            logger.error("sbatch command not found. Is Slurm installed?")
            logger.warning("Service script generated but not submitted.")
            return False
        except Exception as e:
            logger.error(f"Error submitting job: {e}")
            return False
    
    def _generate_slurm_script(self) -> str:
        """
        Generate Slurm submission script for the service
        
        Returns:
            Path to the generated script
        """
        script_dir = Path("scripts/slurm")
        script_dir.mkdir(parents=True, exist_ok=True)
        
        script_path = script_dir / f"{self.service_name}_service.sh"
        
        # Determine container file path
        # Create containers directory if it doesn't exist
        containers_dir = Path("containers")
        containers_dir.mkdir(exist_ok=True)
        
        # Services that don't need containers (run locally)
        no_container_services = ['faiss', 'file_storage']
        
        # Map common service types to existing container files
        service_container_map = {
            'ollama': 'containers/ollama.sif',
            'vllm': 'containers/vllm.sif',
            'chromadb': 'containers/chromadb.sif',
            'weaviate': 'containers/weaviate.sif',
            'postgresql': 'containers/postgres.sif',
            's3': 'containers/minio.sif',
        }
        
        # Skip container setup for services that don't need them
        if self.backend in no_container_services or self.service_type in no_container_services:
            container_sif = None
            pull_container = False
        elif self.container_image:
            # Check if it's already a .sif file path
            if self.container_image.endswith('.sif'):
                container_sif = self.container_image
                pull_container = False
            # Check if it's a docker:// URI
            elif self.container_image.startswith('docker://'):
                # First check if we have a pre-existing container for this service type
                if self.service_type in service_container_map:
                    existing_container = Path(service_container_map[self.service_type])
                    if existing_container.exists():
                        container_sif = str(existing_container)
                        pull_container = False
                        logger.info(f"Using existing container: {container_sif}")
                    else:
                        # Generate filename and check if it exists
                        container_file = self.container_image.replace('docker://', '').replace('/', '_').replace(':', '_')
                        container_sif = f"containers/{container_file}.sif"
                        pull_container = not Path(container_sif).exists()
                else:
                    # Generate filename and check if it exists
                    container_file = self.container_image.replace('docker://', '').replace('/', '_').replace(':', '_')
                    container_sif = f"containers/{container_file}.sif"
                    pull_container = not Path(container_sif).exists()
            else:
                # Assume it's a file path
                container_sif = self.container_image
                pull_container = False
        else:
            # No container image specified, check for pre-existing container
            if self.service_type in service_container_map:
                existing_container = Path(service_container_map[self.service_type])
                if existing_container.exists():
                    container_sif = str(existing_container)
                    pull_container = False
                else:
                    container_sif = f"containers/{self.service_name}.sif"
                    pull_container = not Path(container_sif).exists()
            else:
                container_sif = f"containers/{self.service_name}.sif"
                pull_container = not Path(container_sif).exists()
        
        script_content = f"""#!/bin/bash -l
#SBATCH --job-name={self.service_name}
#SBATCH --time={self.slurm_config.get('time', '01:00:00')}
#SBATCH --partition={self.slurm_config.get('partition', 'gpu')}
#SBATCH --account={self.slurm_config.get('account', 'p200981')}
#SBATCH --nodes={self.slurm_config.get('nodes', 1)}
#SBATCH --ntasks={self.slurm_config.get('ntasks', 1)}
#SBATCH --qos={self.slurm_config.get('qos', 'default')}
#SBATCH --output=logs/{self.service_name}_%j.out
#SBATCH --error=logs/{self.service_name}_%j.err

echo "Date              = $(date)"
echo "Hostname          = $(hostname -s)"
echo "Working Directory = $(pwd)"

# Capture the compute node name
export COMPUTE_NODE=$(hostname -s)
echo "Compute Node      = $COMPUTE_NODE"
export SERVICE_PORT={self.port}
echo "Service Port      = $SERVICE_PORT"

# Export node info to a file that can be read by other processes
mkdir -p $HOME/.cache/service_endpoints
echo "$COMPUTE_NODE:$SERVICE_PORT" > $HOME/.cache/service_endpoints/{self.service_name}_endpoint.txt
echo "Endpoint info saved to: $HOME/.cache/service_endpoints/{self.service_name}_endpoint.txt"
echo "LS of endpoint folder:"
ls $HOME/.cache/service_endpoints/
echo "Endpoint content:"
cat $HOME/.cache/service_endpoints/{self.service_name}_endpoint.txt


# Load required modules
module add Apptainer

"""
        
        # Add container pull logic only if needed
        if pull_container:
            script_content += f"""
# Container not found, pulling from registry
if [ ! -f "{container_sif}" ]; then
    echo "Container not found at {container_sif}"
    echo "Pulling container image from {self.container_image}..."
    mkdir -p containers
    apptainer pull {container_sif} {self.container_image}
else
    echo "Using existing container: {container_sif}"
fi
"""
        else:
            # Only check container file if we actually have one
            if container_sif and container_sif != "None":
                script_content += f"""
# Using existing container image
echo "Using container: {container_sif}"
if [ ! -f "{container_sif}" ]; then
    echo "ERROR: Container file not found: {container_sif}"
    echo "Available containers in containers/:"
    ls -lh containers/ 2>/dev/null || echo "containers/ directory not found"
    exit 1
fi
"""
            else:
                script_content += f"""
# No container needed for this service
echo "Running {self.service_name} without container (local execution)"
"""
        
        script_content += f"""
# Start the service in background
echo "Starting {self.service_name}..."
"""
        
        # Prepare bind mounts for writable directories
        # Use /tmp for writable storage since $PWD might be read-only
        bind_mounts = ""
        if self.service_type == 'vectordb' and self.backend == 'chromadb':
            # ChromaDB needs writable data directory
            script_content += f"""
# Create writable data directory for ChromaDB
export CHROMA_DATA_DIR=/tmp/{self.service_name}_data_$$
mkdir -p $CHROMA_DATA_DIR
"""
            bind_mounts = f"--bind $CHROMA_DATA_DIR:/chroma/data --env CHROMA_DATA_DIR=/chroma/data --env ALLOW_RESET=TRUE"
        elif self.service_type == 'database' and (self.backend == 'postgresql' or 'postgres' in self.service_name.lower()):
            # PostgreSQL needs writable data directory and runtime directory
            script_content += f"""
# Create writable data directory for PostgreSQL
export PGDATA=/tmp/{self.service_name}_data_$$
export PGRUN=/tmp/{self.service_name}_run_$$
mkdir -p $PGDATA
mkdir -p $PGRUN
# Initialize database if needed
if [ ! -f "$PGDATA/PG_VERSION" ]; then
    echo "Initializing PostgreSQL database..."
    apptainer exec {container_sif} initdb -D $PGDATA
fi
"""
            bind_mounts = f"--bind $PGDATA:/var/lib/postgresql/data --bind $PGRUN:/var/run/postgresql"
        elif self.service_type == 's3':
            # MinIO needs writable data directory
            script_content += f"""
# Create writable data directory for MinIO
export MINIO_DATA_DIR=/tmp/{self.service_name}_data_$$
mkdir -p $MINIO_DATA_DIR
"""
            bind_mounts = f"--bind $MINIO_DATA_DIR:/data --env MINIO_ROOT_USER=minioadmin --env MINIO_ROOT_PASSWORD=minioadmin"
        elif self.service_type == 'vectordb' and self.backend == 'weaviate':
            # Weaviate needs writable data directory
            script_content += f"""
# Create writable data directory for Weaviate
export WEAVIATE_DATA_DIR=/tmp/{self.service_name}_data_$$
mkdir -p $WEAVIATE_DATA_DIR
"""
            bind_mounts = f"--bind $WEAVIATE_DATA_DIR:/var/lib/weaviate --env PERSISTENCE_DATA_PATH=/var/lib/weaviate"
        elif self.service_type == 'triton':
            # Triton needs model repository
            script_content += f"""
# Create model repository directory for Triton
export TRITON_MODEL_REPO=/tmp/{self.service_name}_models_$$
mkdir -p $TRITON_MODEL_REPO
echo "WARNING: Triton model repository is empty. Add models to $TRITON_MODEL_REPO for actual inference."
"""
            bind_mounts = f"--bind $TRITON_MODEL_REPO:/models"
        
        # For vLLM, downgrade NumPy first to fix compatibility issue
        if self.service_type == 'vllm':
            script_content += f"""echo "Fixing NumPy version for vLLM compatibility..."
apptainer exec --nv {container_sif} pip install --quiet 'numpy<2.3' 2>/dev/null || echo "NumPy already compatible"
apptainer exec --nv {bind_mounts} {container_sif} {self._get_service_command()} &
"""
        elif container_sif and container_sif != "None":
            script_content += f"""apptainer exec --nv {bind_mounts} {container_sif} {self._get_service_command()} &
"""
        else:
            # No container needed, run command directly
            script_content += f"""{self._get_service_command()} &
"""
        
        script_content += f"""SERVICE_PID=$!
echo "Service started with PID: $SERVICE_PID"

# Wait for service to be ready
echo "Waiting for service to be ready..."
"""
        
        # Add wait time for vLLM services
        if self.service_type == 'vllm':
            script_content += """echo "vLLM takes 60-90 seconds to load the model and capture CUDA graphs..."
sleep 90
"""
        else:
            script_content += """sleep 10
"""
        
        script_content += f"""
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
"""
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_path, 0o755)
        
        logger.info(f"Generated Slurm script: {script_path}")
        return str(script_path)
    
    def _get_service_command(self) -> str:
        """
        Get the command to run inside the container based on service type
        
        Returns:
            Command string
        """
        if self.service_type == 'ollama' or 'ollama' in self.service_name.lower():
            return "ollama serve"
        elif self.service_type == 'vllm':
            # Use python3 and OpenAI-compatible API endpoint
            return f"python3 -m vllm.entrypoints.openai.api_server --model {self.model} --host 0.0.0.0 --port {self.port}"
        elif self.service_type == 'triton':
            # Triton Inference Server
            return f"tritonserver --model-repository=/models --http-port={self.port}"
        elif self.service_type == 'vectordb':
            backend = self.backend or self.service_name
            if 'chromadb' in backend or 'chroma' in self.service_name.lower():
                return f"chroma run --host 0.0.0.0 --port {self.port} --path /chroma/data"
            elif 'faiss' in backend or 'faiss' in self.service_name.lower():
                # FAISS runs as a Python library, not a standalone service
                return "python3 -c 'import time; print(\"FAISS service ready (local library)\"); time.sleep(3600)'"
            elif 'weaviate' in backend or 'weaviate' in self.service_name.lower():
                return f"/bin/weaviate --host 0.0.0.0 --port {self.port} --scheme http"
            else:
                return "echo 'VectorDB service started'"
        elif self.service_type == 'database':
            backend = self.backend or 'postgresql'
            if backend == 'postgresql' or 'postgres' in self.service_name.lower():
                # PostgreSQL startup command
                return f"postgres -D /var/lib/postgresql/data -p {self.port}"
            else:
                return "echo 'Database service started'"
        elif self.service_type == 's3':
            # MinIO server
            data_dir = getattr(self, 'data_dir', '/data')
            return f"minio server {data_dir} --address 0.0.0.0:9000 --console-address 0.0.0.0:9001"
        elif self.service_type == 'file_storage':
            # File storage doesn't need a service, it's direct filesystem access
            return "python3 -c 'import time; print(\"File storage service ready\"); time.sleep(3600)'"
        else:
            logger.warning(f"Unknown service type: {self.service_type}, using placeholder command")
            return "echo 'Service started'"
    
    def stop_service(self) -> bool:
        """
        Stop the running service
        
        Returns:
            True if service stopped successfully
        """
        if self.job_id:
            logger.info(f"Stopping service {self.service_name} (job {self.job_id})")
            try:
                subprocess.run(['scancel', str(self.job_id)], check=True)
                return True
            except Exception as e:
                logger.error(f"Failed to stop service: {e}")
                return False
        else:
            logger.warning("No job ID found for service")
            return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get the current status of the service
        
        Returns:
            Dictionary with service status information
        """
        status = {
            'service_name': self.service_name,
            'job_id': self.job_id,
            'container_image': self.container_image,
            'port': self.port,
            'status': 'not_started' if not self.job_id else 'submitted'
        }
        
        # If job is submitted, get its Slurm status
        if self.job_id:
            slurm_status = self.get_slurm_job_status()
            if slurm_status:
                status['slurm_state'] = slurm_status['state']
                status['slurm_reason'] = slurm_status['reason']
                
                # Map Slurm states to friendly status
                slurm_state = slurm_status['state']
                if slurm_state in ['RUNNING', 'COMPLETING']:
                    status['status'] = 'running'
                elif slurm_state in ['PENDING', 'CONFIGURING']:
                    status['status'] = 'pending'
                elif slurm_state in ['COMPLETED']:
                    status['status'] = 'completed'
                elif slurm_state in ['FAILED', 'TIMEOUT', 'CANCELLED', 'NODE_FAIL']:
                    status['status'] = 'failed'
                elif slurm_state == 'NOT_FOUND':
                    status['status'] = 'not_found'
        
        return status
    
    def get_service_endpoint(self) -> Optional[str]:
        """
        Get the service endpoint (node:port) where the service is running
        
        This reads the endpoint info file created by the Slurm job
        
        Returns:
            Endpoint string in format "nodeXYZ:port" or None if not available
        """
        home_dir = os.environ.get('HOME', os.path.expanduser('~'))
        endpoint_file = Path(f"{home_dir}/.cache/service_endpoints/{self.service_name}_endpoint.txt")
        
        try:
            if endpoint_file.exists():
                endpoint = endpoint_file.read_text().strip()
                logger.info(f"Service endpoint: {endpoint}")
                return endpoint
            else:
                logger.warning(f"Endpoint file not found: {endpoint_file}")
                return None
        except Exception as e:
            logger.error(f"Failed to read endpoint file: {e}")
            return None
    
    def get_service_url(self) -> Optional[str]:
        """
        Get the full service URL
        
        Returns:
            Full URL like "http://nodeXYZ:port" or None if not available
        """
        endpoint = self.get_service_endpoint()
        if endpoint:
            return f"http://{endpoint}"
        return None
    
    def get_slurm_job_status(self) -> Optional[Dict[str, str]]:
        """
        Get the Slurm job status using squeue
        
        Returns:
            Dictionary with job status info or None if job not found
        """
        if not self.job_id:
            logger.warning("No job ID available")
            return None
        
        try:
            result = subprocess.run(
                ['squeue', '-j', self.job_id, '-o', '%T,%R', '-h'],
                capture_output=True,
                text=True,
                check=True
            )
            
            output = result.stdout.strip()
            if output:
                parts = output.split(',')
                status = {
                    'job_id': self.job_id,
                    'state': parts[0] if len(parts) > 0 else 'UNKNOWN',
                    'reason': parts[1] if len(parts) > 1 else 'N/A'
                }
                return status
            else:
                # Job not in queue (may have completed or failed)
                return {
                    'job_id': self.job_id,
                    'state': 'NOT_FOUND',
                    'reason': 'Job not in queue'
                }
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to query job status: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Error querying job status: {e}")
            return None


class ServerOrchestrator:
    """Orchestrates multiple services"""
    
    def __init__(self, services_config: List[Dict[str, Any]]):
        """
        Initialize server orchestrator
        
        Args:
            services_config: List of service configurations
        """
        self.services = [ServiceManager(config) for config in services_config]
        
    def start_all_services(self):
        """Start all configured services"""
        logger.info(f"Starting {len(self.services)} services...")
        for service in self.services:
            service.start_service()
            time.sleep(1)  # Small delay between service starts
    
    def stop_all_services(self):
        """Stop all running services"""
        logger.info(f"Stopping {len(self.services)} services...")
        for service in self.services:
            service.stop_service()
    
    def get_all_services_status(self) -> List[Dict[str, Any]]:
        """Get status of all services"""
        return [service.get_service_status() for service in self.services]


if __name__ == "__main__":
    # Example usage
    config = {
        'service_name': 'ollama-llama2',
        'container_image': 'docker://ollama/ollama',
        'service_type': 'ollama',
        'port': 11434,
        'slurm': {
            'partition': 'gpu',
            'time': '00:30:00',
            'nodes': 1
        }
    }
    manager = ServiceManager(config)
    manager.start_service()
