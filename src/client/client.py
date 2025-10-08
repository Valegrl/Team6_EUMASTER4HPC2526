#!/usr/bin/env python3
"""
Client Component
Handles request generation and execution against benchmark services
"""

import time
import logging
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RequestResult:
    """Result of a single request"""
    timestamp: float
    duration: float
    success: bool
    status_code: Optional[int] = None
    error: Optional[str] = None
    response_size: int = 0


class BenchmarkClient:
    """Client for executing benchmark requests against services"""
    
    def __init__(self, service_config: Dict[str, Any]):
        """
        Initialize benchmark client
        
        Args:
            service_config: Service configuration from recipe
        """
        self.service_name = service_config.get('service_name')
        self.service_type = service_config.get('service_type', 'ollama')
        self.client_count = service_config.get('client_count', 1)
        self.requests_per_second = service_config.get('requests_per_second', 10)
        self.service_url = service_config.get('service_url', 'http://localhost:11434')
        self.duration = service_config.get('duration', 60)
        self.model = service_config.get('model', 'llama2')
        self.results: List[RequestResult] = []
        
    def setup(self):
        """Setup the client (called before starting requests)"""
        logger.info(f"Setting up client for {self.service_name}")
        logger.info(f"Client count: {self.client_count}, RPS: {self.requests_per_second}")
        
    def send_request(self) -> RequestResult:
        """
        Send a single request to the service
        
        Returns:
            RequestResult with timing and status information
        """
        start_time = time.time()
        try:
            # Dispatch request based on service type
            if self.service_type == 'ollama':
                response = self._send_ollama_request()
            elif self.service_type == 'vllm':
                response = self._send_vllm_request()
            elif self.service_type == 'vectordb':
                response = self._send_vectordb_request()
            elif self.service_type == 'database':
                response = self._send_database_request()
            else:
                # Generic HTTP POST for unknown types
                response = requests.post(
                    self.service_url,
                    json={"test": "benchmark"},
                    timeout=30
                )
            
            duration = time.time() - start_time
            
            return RequestResult(
                timestamp=start_time,
                duration=duration,
                success=response.status_code == 200,
                status_code=response.status_code,
                response_size=len(response.content)
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.debug(f"Request failed: {e}")
            return RequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                error=str(e)
            )
    
    def _send_ollama_request(self):
        """Send request to Ollama service"""
        return requests.post(
            f"{self.service_url}/api/generate",
            json={
                "model": self.model,
                "prompt": "Hello, this is a benchmark test.",
                "stream": False
            },
            timeout=30
        )
    
    def _send_vllm_request(self):
        """Send request to vLLM service"""
        return requests.post(
            f"{self.service_url}/v1/completions",
            json={
                "model": self.model,
                "prompt": "Hello, this is a benchmark test.",
                "max_tokens": 50
            },
            timeout=30
        )
    
    def _send_vectordb_request(self):
        """Send request to vector database (ChromaDB)"""
        # Simple query to test vector database
        return requests.post(
            f"{self.service_url}/api/v1/collections/test/query",
            json={
                "query_texts": ["benchmark test"],
                "n_results": 10
            },
            timeout=30
        )
    
    def _send_database_request(self):
        """Send request to database (PostgreSQL via HTTP proxy if available)"""
        # For databases, we'd typically use a connection library
        # For benchmarking, we'll use a simple health check or query endpoint
        return requests.get(
            f"{self.service_url}/health",
            timeout=30
        )
    
    def run_client(self, client_id: int):
        """
        Run a single client thread
        
        Args:
            client_id: Identifier for this client thread
        """
        logger.info(f"Starting client {client_id}")
        interval = 1.0 / self.requests_per_second
        start = time.time()
        
        while time.time() - start < self.duration:
            result = self.send_request()
            self.results.append(result)
            
            # Sleep to maintain target RPS
            time.sleep(interval)
        
        logger.info(f"Client {client_id} completed")
    
    def run(self) -> List[RequestResult]:
        """
        Run the benchmark with multiple clients
        
        Returns:
            List of all request results
        """
        self.setup()
        threads = []
        
        for i in range(self.client_count):
            t = threading.Thread(target=self.run_client, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        logger.info(f"Benchmark completed. Total requests: {len(self.results)}")
        return self.results
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of the benchmark run
        
        Returns:
            Dictionary with summary statistics
        """
        if not self.results:
            return {}
        
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        durations = [r.duration for r in successful]
        
        return {
            'total_requests': len(self.results),
            'successful': len(successful),
            'failed': len(failed),
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
        }


if __name__ == "__main__":
    # Example usage
    config = {
        'service_name': 'ollama-test',
        'client_count': 2,
        'requests_per_second': 5,
        'duration': 10
    }
    client = BenchmarkClient(config)
    results = client.run()
    print(client.get_summary())
