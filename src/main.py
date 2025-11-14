#!/usr/bin/env python3
"""
Main Orchestrator
Coordinates all components to run a complete benchmark
"""

import sys
import time
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from middleware.interface import MiddlewareInterface
from client.client import BenchmarkClient
from server.server import ServiceManager
from monitor.monitor import Monitor
from reporter.reporter import BenchmarkReporter
from logger.logger import BenchmarkLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BenchmarkOrchestrator:
    """Main orchestrator for the benchmarking framework"""
    
    def __init__(self, recipe_path: str = "recipe.yml"):
        """
        Initialize the orchestrator
        
        Args:
            recipe_path: Path to recipe configuration
        """
        self.interface = MiddlewareInterface(recipe_path)
        self.benchmark_id = None
        self.benchmark_logger = None
        self.monitor = None
        self.services = []
        self.clients = []
        
    def run_benchmark(self):
        """Execute the complete benchmark workflow"""
        try:
            # Step 1: Start recipe via interface
            logger.info("Step 1: Starting recipe...")
            result = self.interface.start_recipe()
            self.benchmark_id = result['benchmark_id']
            
            # Initialize logger and monitor
            self.benchmark_logger = BenchmarkLogger(self.benchmark_id)
            self.monitor = Monitor(self.benchmark_id)
            
            # Log benchmark start
            self.benchmark_logger.log_benchmark_start({
                'services': result['services']
            })
            
            # Step 2: Get services info
            logger.info("Step 2: Getting services information...")
            services_config = self.interface.get_services_info()
            self.benchmark_logger.logger.info(f"Found {len(services_config)} services to benchmark")
            
            # Step 3: Start services
            logger.info("Step 3: Starting services...")
            for service_config in services_config:
                service_manager = ServiceManager(service_config)
                service_manager.start_service()
                self.services.append(service_manager)
                self.benchmark_logger.log_service_start(
                    service_config['service_name'],
                    service_config
                )
            
            # Wait for services to be ready
            logger.info("Waiting for services to initialize...")
            time.sleep(30)  # Increased wait time for services to fully start
            
            # Step 3.5: Retrieve service endpoints
            logger.info("Step 3.5: Retrieving service endpoints...")
            service_endpoints = {}
            for service_manager in self.services:
                service_name = service_manager.service_name
                
                # Try to get endpoint with retries
                max_retries = 10
                endpoint_url = None
                for attempt in range(max_retries):
                    endpoint_url = service_manager.get_service_url()
                    if endpoint_url:
                        logger.info(f"  {service_name}: {endpoint_url}")
                        service_endpoints[service_name] = endpoint_url
                        break
                    else:
                        logger.warning(f"  {service_name}: Endpoint not ready, retrying ({attempt+1}/{max_retries})...")
                        time.sleep(3)
                
                if not endpoint_url:
                    logger.error(f"  {service_name}: Failed to retrieve endpoint after {max_retries} attempts")
                    raise RuntimeError(f"Service {service_name} endpoint not available")
            
            logger.info(f"Retrieved {len(service_endpoints)} service endpoints")
            
            # Step 4: Setup clients and run benchmarks
            logger.info("Step 4: Running benchmarks...")
            for service_config in services_config:
                service_name = service_config['service_name']
                logger.info(f"Benchmarking service: {service_name}")
                
                # Get the actual service URL from the endpoint we retrieved
                if service_name in service_endpoints:
                    service_config['service_url'] = service_endpoints[service_name]
                    logger.info(f"  Using service URL: {service_config['service_url']}")
                else:
                    logger.error(f"  No endpoint found for {service_name}, skipping...")
                    continue
                
                # Create and run client with the actual service URL
                client = BenchmarkClient(service_config)
                
                # Log benchmark configuration
                logger.info(f"  Client count: {client.client_count}")
                logger.info(f"  Requests per second: {client.requests_per_second}")
                logger.info(f"  Duration: {client.duration}s")
                
                # Run the actual benchmark
                from interceptor.interceptor import MetricsInterceptor
                interceptor = MetricsInterceptor(service_name)
                
                try:
                    # Execute real benchmark
                    logger.info(f"  Starting real benchmark execution...")
                    results = client.run()
                    
                    # Convert RequestResults to metrics format
                    for idx, result in enumerate(results):
                        interceptor.record_metrics(
                            client_id=f"client-{idx % client.client_count}",
                            duration=result.duration,
                            success=result.success,
                            status_code=result.status_code,
                            error=result.error,
                            response_size=result.response_size
                        )
                    
                    logger.info(f"  Completed {len(results)} requests")
                    
                except Exception as e:
                    logger.error(f"  Benchmark execution failed: {e}")
                    # Even on failure, record whatever metrics we have
                
                # Store metrics
                metrics = interceptor.get_metrics()
                self.monitor.record_metrics(service_name, metrics)
                
                self.benchmark_logger.log_results(service_name, {
                    'total_requests': len(metrics),
                    'successful': sum(1 for m in metrics if m['success']),
                    'failed': sum(1 for m in metrics if not m['success']),
                    'avg_duration': sum(m['request_duration'] for m in metrics) / len(metrics)
                })
                
                self.clients.append(client)
            
            # Step 5: Generate report
            logger.info("Step 5: Generating report...")
            all_metrics = self.monitor.get_data()
            reporter = BenchmarkReporter(self.benchmark_id)
            report = reporter.generate_report(all_metrics)
            reporter.save_report(report)
            
            # Print summary
            summary = reporter.generate_text_summary(report)
            print(summary)
            self.benchmark_logger.logger.info(summary)
            
            # Log benchmark end
            self.benchmark_logger.log_benchmark_end({
                'total_requests': len(all_metrics),
                'success_rate': report['summary'].get('success_rate', 0)
            })
            
            # Step 6: Cleanup
            logger.info("Step 6: Stopping services...")
            for service in self.services:
                service.stop_service()
                self.benchmark_logger.log_service_stop(service.service_name)
            
            logger.info(f"Benchmark completed! ID: {self.benchmark_id}")
            logger.info(f"Report saved to: reports/{self.benchmark_id}_report.json")
            logger.info(f"Logs saved to: logs/{self.benchmark_id}.log")
            
            return report
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}", exc_info=True)
            if self.benchmark_logger:
                self.benchmark_logger.log_error("Benchmark execution failed", e)
            raise


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Factory Benchmarking Framework')
    parser.add_argument('--recipe', default='recipe.yml',
                       help='Path to recipe configuration file')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("AI Factory Benchmarking Framework")
    logger.info("=" * 60)
    
    orchestrator = BenchmarkOrchestrator(args.recipe)
    orchestrator.run_benchmark()


if __name__ == "__main__":
    main()
