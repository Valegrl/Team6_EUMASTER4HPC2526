#!/usr/bin/env python3
"""
Logger Component
Handles logging of requests, responses, and benchmark operations
"""

import logging
import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import sys

# Configure base logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class BenchmarkLogger:
    """Logger for benchmark operations and results"""
    
    def __init__(self, benchmark_id: str, log_dir: str = "logs"):
        """
        Initialize benchmark logger
        
        Args:
            benchmark_id: Unique benchmark identifier
            log_dir: Directory to store log files
        """
        self.benchmark_id = benchmark_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logger instance
        self.logger = logging.getLogger(f"benchmark.{benchmark_id}")
        self.logger.setLevel(logging.DEBUG)
        
        # File handler for detailed logs
        log_file = self.log_dir / f"{benchmark_id}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Console handler for important messages
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"Initialized logger for benchmark {benchmark_id}")
    
    def log_request(self, 
                   service_name: str,
                   client_id: str,
                   request_data: Optional[Dict[str, Any]] = None):
        """
        Log a request being made
        
        Args:
            service_name: Name of the service
            client_id: Client identifier
            request_data: Optional request details
        """
        message = f"Request from {client_id} to {service_name}"
        if request_data:
            message += f" - Data: {json.dumps(request_data)}"
        
        self.logger.debug(message)
    
    def log_response(self,
                    service_name: str,
                    client_id: str,
                    success: bool,
                    duration: float,
                    status_code: Optional[int] = None,
                    error: Optional[str] = None):
        """
        Log a response received
        
        Args:
            service_name: Name of the service
            client_id: Client identifier
            success: Whether the request was successful
            duration: Request duration in seconds
            status_code: HTTP status code
            error: Error message if failed
        """
        if success:
            message = f"Response from {service_name} to {client_id} - " \
                     f"Duration: {duration:.3f}s, Status: {status_code}"
            self.logger.debug(message)
        else:
            message = f"Failed response from {service_name} to {client_id} - " \
                     f"Duration: {duration:.3f}s, Error: {error}"
            self.logger.warning(message)
    
    def log_results(self, 
                   service_name: str,
                   results_summary: Dict[str, Any]):
        """
        Log benchmark results summary
        
        Args:
            service_name: Name of the service
            results_summary: Summary of results
        """
        self.logger.info(f"Results for {service_name}:")
        self.logger.info(f"  Total requests: {results_summary.get('total_requests', 0)}")
        self.logger.info(f"  Successful: {results_summary.get('successful', 0)}")
        self.logger.info(f"  Failed: {results_summary.get('failed', 0)}")
        self.logger.info(f"  Avg duration: {results_summary.get('avg_duration', 0):.3f}s")
    
    def log_service_start(self, service_name: str, config: Dict[str, Any]):
        """
        Log service startup
        
        Args:
            service_name: Name of the service
            config: Service configuration
        """
        self.logger.info(f"Starting service: {service_name}")
        self.logger.debug(f"Service config: {json.dumps(config, indent=2)}")
    
    def log_service_stop(self, service_name: str):
        """
        Log service shutdown
        
        Args:
            service_name: Name of the service
        """
        self.logger.info(f"Stopping service: {service_name}")
    
    def log_benchmark_start(self, config: Dict[str, Any]):
        """
        Log benchmark start
        
        Args:
            config: Benchmark configuration
        """
        self.logger.info("=" * 60)
        self.logger.info(f"Starting benchmark: {self.benchmark_id}")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger.info(f"Configuration: {json.dumps(config, indent=2)}")
        self.logger.info("=" * 60)
    
    def log_benchmark_end(self, summary: Dict[str, Any]):
        """
        Log benchmark completion
        
        Args:
            summary: Benchmark summary
        """
        self.logger.info("=" * 60)
        self.logger.info(f"Benchmark completed: {self.benchmark_id}")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger.info(f"Summary: {json.dumps(summary, indent=2)}")
        self.logger.info("=" * 60)
    
    def log_error(self, error_message: str, exception: Optional[Exception] = None):
        """
        Log an error
        
        Args:
            error_message: Error message
            exception: Optional exception object
        """
        if exception:
            self.logger.error(f"{error_message}: {str(exception)}", exc_info=True)
        else:
            self.logger.error(error_message)
    
    def retrieve_logs(self) -> str:
        """
        Retrieve all logs for this benchmark
        
        Returns:
            Log content as string
        """
        log_file = self.log_dir / f"{self.benchmark_id}.log"
        if log_file.exists():
            with open(log_file, 'r') as f:
                return f.read()
        else:
            return ""


if __name__ == "__main__":
    # Example usage
    logger = BenchmarkLogger("test_benchmark_001")
    
    logger.log_benchmark_start({
        'services': ['ollama', 'vllm'],
        'duration': 60
    })
    
    logger.log_service_start('ollama', {'port': 11434})
    logger.log_request('ollama', 'client-1', {'prompt': 'test'})
    logger.log_response('ollama', 'client-1', True, 0.5, 200)
    logger.log_service_stop('ollama')
    
    logger.log_benchmark_end({
        'total_requests': 100,
        'success_rate': 98.5
    })
    
    print("\nLogs:")
    print(logger.retrieve_logs())
