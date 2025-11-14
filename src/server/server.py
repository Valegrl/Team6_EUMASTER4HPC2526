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
        if self.container_image:
            # Check if it's already a .sif file path
            if self.container_image.endswith('.sif'):
                container_sif = self.container_image
                pull_container = False
            # Check if it's a docker:// URI
            elif self.container_image.startswith('docker://'):
                container_file = self.container_image.replace('docker://', '').replace('/', '_').replace(':', '_')
                container_sif = f"{container_file}.sif"
                pull_container = True
            else:
                # Assume it's a file path
                container_sif = self.container_image
                pull_container = False
        else:
            container_sif = f"{self.service_name}.sif"
            pull_container = False
        
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
mkdir -p /tmp/$USER
echo "$COMPUTE_NODE:$SERVICE_PORT" > /tmp/$USER/{self.service_name}_endpoint.txt
echo "Endpoint info saved to: /tmp/$USER/{self.service_name}_endpoint.txt"

# Load required modules
module add Apptainer

"""
        
        # Add container pull logic only if needed
        if pull_container:
            script_content += f"""
# Pull container if needed
if [ ! -f "{container_sif}" ]; then
    echo "Pulling container image..."
    apptainer pull {container_sif} {self.container_image}
fi
"""
        else:
            script_content += f"""
# Using existing container image
echo "Container image: {container_sif}"
if [ ! -f "{container_sif}" ]; then
    echo "ERROR: Container file not found: {container_sif}"
    exit 1
fi
"""
        
        script_content += f"""
# Start the service in background
echo "Starting {self.service_name}..."
apptainer exec --nv {container_sif} {self._get_service_command()} &
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
            return "python -m vllm.entrypoints.api_server"
        else:
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
        endpoint_file = Path(f"/tmp/{os.environ.get('USER', 'user')}/{self.service_name}_endpoint.txt")
        
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
