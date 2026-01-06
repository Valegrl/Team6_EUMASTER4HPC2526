#!/usr/bin/env python3
"""
Unified Benchmark Client Factory

Creates and manages specialized benchmark clients for different service types.
Provides a unified interface for all benchmarking operations.
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from client.client import BenchmarkClient, RequestResult
from client.postgres_client import PostgreSQLBenchmarkClient, PostgreSQLRequestResult
from client.s3_client import S3BenchmarkClient, S3RequestResult
from client.file_storage_client import FileStorageBenchmarkClient, FileStorageRequestResult
from client.vectordb_client import VectorDBBenchmarkClient, VectorDBRequestResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedBenchmarkClient:
    """Unified client that delegates to specialized clients based on service type"""
    
    def __init__(self, service_config: Dict[str, Any]):
        """
        Initialize unified benchmark client
        
        Args:
            service_config: Service configuration from recipe
        """
        self.service_config = service_config
        self.service_type = service_config.get('service_type', 'http')
        self.service_name = service_config.get('service_name', 'unknown')
        self.client = None
        self.results = []
        
        logger.info(f"Initializing unified client for {self.service_name} ({self.service_type})")
        
        # Create appropriate specialized client
        self._create_client()
    
    def _create_client(self):
        """Create the appropriate specialized client based on service type"""
        if self.service_type in ['ollama', 'vllm', 'triton']:
            # HTTP-based LLM inference services
            self.client = BenchmarkClient(self.service_config)
            
        elif self.service_type == 'database':
            backend = self.service_config.get('backend', 'postgresql')
            if backend == 'postgresql':
                self.client = PostgreSQLBenchmarkClient(self.service_config)
            else:
                logger.warning(f"Unsupported database backend: {backend}, using HTTP client")
                self.client = BenchmarkClient(self.service_config)
        
        elif self.service_type == 's3':
            self.client = S3BenchmarkClient(self.service_config)
        
        elif self.service_type == 'file_storage':
            self.client = FileStorageBenchmarkClient(self.service_config)
        
        elif self.service_type == 'vectordb':
            self.client = VectorDBBenchmarkClient(self.service_config)
        
        else:
            # Default to HTTP benchmark client
            logger.info(f"Using default HTTP client for service type: {self.service_type}")
            self.client = BenchmarkClient(self.service_config)
    
    def setup(self):
        """Setup the client before benchmarking"""
        logger.info(f"Setting up {self.service_type} client...")
        
        try:
            if hasattr(self.client, 'connect'):
                if not self.client.connect():
                    logger.error(f"Failed to connect to {self.service_name}")
                    return False
            
            if hasattr(self.client, 'setup'):
                if hasattr(self.client, 'setup_bucket'):
                    self.client.setup_bucket()
                elif hasattr(self.client, 'setup_test_table'):
                    self.client.setup_test_table()
                else:
                    self.client.setup()
            
            logger.info(f"Client setup complete for {self.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Setup failed for {self.service_name}: {e}")
            return False
    
    def run(self) -> List[RequestResult]:
        """
        Run the benchmark
        
        Returns:
            List of request results
        """
        logger.info(f"Starting benchmark for {self.service_name}...")
        
        try:
            # For HTTP-based clients, use existing run method
            if isinstance(self.client, BenchmarkClient):
                self.results = self.client.run()
                return self.results
            
            # For specialized clients, we need to implement the benchmark loop
            import threading
            import time
            
            client_count = self.service_config.get('client_count', 1)
            requests_per_second = self.service_config.get('requests_per_second', 10)
            duration = self.service_config.get('duration', 60)
            
            def run_client_thread(client_id: int):
                """Run a single client thread"""
                interval = 1.0 / requests_per_second
                start = time.time()
                thread_results = []
                
                while time.time() - start < duration:
                    try:
                        # Execute operation based on client type
                        result = self.client.execute_operation()
                        
                        # Convert specialized result to RequestResult
                        converted_result = self._convert_result(result)
                        thread_results.append(converted_result)
                        
                    except Exception as e:
                        logger.error(f"Client {client_id} error: {e}")
                    
                    # Sleep to maintain target RPS
                    time.sleep(interval)
                
                return thread_results
            
            # Run multiple client threads
            threads = []
            all_results = []
            
            for i in range(client_count):
                t = threading.Thread(target=lambda cid=i: all_results.extend(run_client_thread(cid)))
                threads.append(t)
                t.start()
            
            # Wait for all threads to complete
            for t in threads:
                t.join()
            
            self.results = all_results
            logger.info(f"Benchmark completed for {self.service_name}. Total operations: {len(self.results)}")
            return self.results
            
        except Exception as e:
            logger.error(f"Benchmark failed for {self.service_name}: {e}")
            return []
    
    def _convert_result(self, result) -> RequestResult:
        """Convert specialized result types to standard RequestResult"""
        if isinstance(result, RequestResult):
            return result
        
        # Convert other result types
        return RequestResult(
            timestamp=result.timestamp,
            duration=result.duration,
            success=result.success,
            status_code=200 if result.success else 500,
            error=getattr(result, 'error', None),
            response_size=getattr(result, 'bytes_transferred', 0) or 
                         getattr(result, 'response_size', 0) or
                         getattr(result, 'vectors_processed', 0) or
                         getattr(result, 'rows_affected', 0)
        )
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info(f"Cleaning up {self.service_name}...")
        
        try:
            if hasattr(self.client, 'cleanup'):
                self.client.cleanup()
            
            if hasattr(self.client, 'close'):
                self.client.close()
            
            logger.info(f"Cleanup complete for {self.service_name}")
            
        except Exception as e:
            logger.warning(f"Cleanup error for {self.service_name}: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get benchmark summary statistics"""
        if not self.results:
            return {
                'total_requests': 0,
                'successful': 0,
                'failed': 0,
                'avg_duration': 0,
                'min_duration': 0,
                'max_duration': 0
            }
        
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        durations = [r.duration for r in successful]
        
        return {
            'service_name': self.service_name,
            'service_type': self.service_type,
            'total_requests': len(self.results),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': (len(successful) / len(self.results) * 100) if self.results else 0,
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
        }


def create_benchmark_client(service_config: Dict[str, Any]) -> UnifiedBenchmarkClient:
    """
    Factory function to create a unified benchmark client
    
    Args:
        service_config: Service configuration from recipe
        
    Returns:
        UnifiedBenchmarkClient instance
    """
    return UnifiedBenchmarkClient(service_config)
