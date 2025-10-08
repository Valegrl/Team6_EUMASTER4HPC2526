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
        
        # In a real deployment, this would submit a Slurm job
        # For now, we'll create a script and log the action
        script_path = self._generate_slurm_script()
        
        logger.info(f"Service {self.service_name} configured with script: {script_path}")
        logger.info(f"Container image: {self.container_image}")
        logger.info(f"Port: {self.port}")
        
        return True
    
    def _generate_slurm_script(self) -> str:
        """
        Generate Slurm submission script for the service
        
        Returns:
            Path to the generated script
        """
        script_dir = Path("scripts/slurm")
        script_dir.mkdir(parents=True, exist_ok=True)
        
        script_path = script_dir / f"{self.service_name}_service.sh"
        
        # Generate container file name if container_image is provided
        if self.container_image:
            container_file = self.container_image.replace('docker://', '').replace('/', '_').replace(':', '_')
            container_sif = f"{container_file}.sif"
        else:
            container_sif = f"{self.service_name}.sif"
            container_file = self.service_name
        
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

# Load required modules
module add Apptainer

# Pull container if needed
if [ ! -f "{container_sif}" ]; then
    echo "Pulling container image..."
    apptainer pull {self.container_image or 'docker://alpine:latest'}
fi

# Start the service
echo "Starting {self.service_name}..."
apptainer exec --nv {container_sif} {self._get_service_command()}
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
        return {
            'service_name': self.service_name,
            'job_id': self.job_id,
            'container_image': self.container_image,
            'port': self.port,
            'status': 'configured'
        }


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
