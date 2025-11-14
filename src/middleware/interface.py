#!/usr/bin/env python3
"""
Middleware Interface Component
Provides user interface for starting and managing benchmarking recipes
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MiddlewareInterface:
    """Main interface for interacting with the benchmarking framework"""
    
    def __init__(self, recipe_path: str = "recipe.yml"):
        """
        Initialize the middleware interface
        
        Args:
            recipe_path: Path to the recipe configuration file
        """
        self.recipe_path = recipe_path
        self.recipe_config = None
        self.benchmark_id = None
        
    def load_recipe(self) -> Dict[str, Any]:
        """Load the recipe configuration from YAML file"""
        try:
            with open(self.recipe_path, 'r') as f:
                self.recipe_config = yaml.safe_load(f)
            logger.info(f"Recipe loaded from {self.recipe_path}")
            return self.recipe_config
        except Exception as e:
            logger.error(f"Failed to load recipe: {e}")
            raise
    
    def start_recipe(self) -> Dict[str, Any]:
        """
        Start the benchmarking recipe
        
        Returns:
            Dictionary with benchmark ID and status
        """
        if not self.recipe_config:
            self.load_recipe()
        
        import time
        self.benchmark_id = f"benchmark_{int(time.time())}"
        
        logger.info(f"Starting recipe with ID: {self.benchmark_id}")
        logger.info(f"Services to benchmark: {len(self.recipe_config.get('services', []))}")
        
        return {
            'benchmark_id': self.benchmark_id,
            'status': 'started',
            'services': self.recipe_config.get('services', [])
        }
    
    def get_services_info(self) -> list:
        """
        Get information about services defined in the recipe
        
        Returns:
            List of service configurations
        """
        if not self.recipe_config:
            self.load_recipe()
        
        services = self.recipe_config.get('services', [])
        logger.info(f"Retrieved info for {len(services)} services")
        return services
    
    def retrieve_report(self, benchmark_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve benchmark report by ID
        
        Args:
            benchmark_id: The benchmark identifier
            
        Returns:
            Report data if available
        """
        report_path = f"reports/{benchmark_id}_report.json"
        if os.path.exists(report_path):
            import json
            with open(report_path, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Report not found for ID: {benchmark_id}")
            return None
    
    def retrieve_logs(self, benchmark_id: str) -> Optional[str]:
        """
        Retrieve logs for a specific benchmark
        
        Args:
            benchmark_id: The benchmark identifier
            
        Returns:
            Log content if available
        """
        log_path = f"logs/{benchmark_id}.log"
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                return f.read()
        else:
            logger.warning(f"Logs not found for ID: {benchmark_id}")
            return None


if __name__ == "__main__":
    # Example usage
    interface = MiddlewareInterface()
    result = interface.start_recipe()
    print(f"Started benchmark: {result}")
