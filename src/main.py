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
from client.unified_client import create_benchmark_client
from server.server import ServiceManager
from monitor.monitor import Monitor
from reporter.reporter import BenchmarkReporter
from logger.logger import BenchmarkLogger
from monitoring.prometheus_exporter import PrometheusExporter
from utils.cli_utils import (
    print_banner, print_section, print_subsection,
    print_info, print_success, print_warning, print_error,
    print_benchmark_config, print_benchmark_results,
    print_monitoring_info, print_completion_banner
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BenchmarkOrchestrator:
    """Main orchestrator for the benchmarking framework"""
    
    def __init__(self, recipe_path: str = "recipe.yml", pushgateway_url: str = None):
        """
        Initialize the orchestrator
        
        Args:
            recipe_path: Path to recipe configuration
            pushgateway_url: Optional Pushgateway URL (overrides recipe config)
        """
        self.interface = MiddlewareInterface(recipe_path)
        self.benchmark_id = None
        self.benchmark_logger = None
        self.monitor = None
        self.services = []
        self.clients = []
        self.pushgateway_url = pushgateway_url
        
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
                    logger.warning(f"  No endpoint found for {service_name}, using config URL...")
                
                # Create unified client (automatically selects appropriate client type)
                client = create_benchmark_client(service_config)
                
                # Setup client
                if not client.setup():
                    logger.error(f"  Failed to setup client for {service_name}, skipping...")
                    continue
                
                # Log benchmark configuration
                logger.info(f"  Client count: {service_config.get('client_count', 1)}")
                logger.info(f"  Requests per second: {service_config.get('requests_per_second', 10)}")
                logger.info(f"  Duration: {service_config.get('duration', 60)}s")
                
                # Run the actual benchmark
                from interceptor.interceptor import MetricsInterceptor
                interceptor = MetricsInterceptor(service_name)
                
                try:
                    # Execute real benchmark
                    logger.info(f"  Starting benchmark execution...")
                    results = client.run()
                    
                    # Convert results to metrics format
                    for idx, result in enumerate(results):
                        interceptor.record_metrics(
                            client_id=f"client-{idx % service_config.get('client_count', 1)}",
                            duration=result.duration,
                            success=result.success,
                            status_code=result.status_code,
                            error=result.error,
                            response_size=result.response_size
                        )
                    
                    logger.info(f"  Completed {len(results)} operations")
                    
                    # Print summary
                    summary = client.get_summary()
                    logger.info(f"  Summary: {summary['successful']}/{summary['total_requests']} successful ({summary['success_rate']:.2f}%)")
                    logger.info(f"  Avg latency: {summary['avg_duration']:.3f}s")
                    
                except Exception as e:
                    logger.error(f"  Benchmark execution failed: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    # Always cleanup
                    client.cleanup()
                
                # Store metrics
                metrics = interceptor.get_metrics()
                self.monitor.record_metrics(service_name, metrics)
                
                self.benchmark_logger.log_results(service_name, {
                    'total_requests': len(metrics),
                    'successful': sum(1 for m in metrics if m['success']),
                    'failed': sum(1 for m in metrics if not m['success']),
                    'avg_duration': sum(m['request_duration'] for m in metrics) / len(metrics) if metrics else 0
                })
                
                self.clients.append(client)
            
            # Step 5: Generate report
            logger.info("Step 5: Generating report...")
            all_metrics = self.monitor.get_data()
            reporter = BenchmarkReporter(self.benchmark_id)
            report = reporter.generate_report(all_metrics)
            reporter.save_report(report)
            
            # Step 5.5: Push metrics to Prometheus Pushgateway (if configured)
            import os
            pushgateway_url = (
                self.pushgateway_url or 
                self.interface.config.get('global', {}).get('pushgateway_url') or
                os.environ.get('PUSHGATEWAY_URL')
            )
            if pushgateway_url:
                logger.info(f"Step 5.5: Pushing metrics to Prometheus Pushgateway...")
                try:
                    exporter = PrometheusExporter(self.monitor)
                    success = exporter.push_to_gateway(pushgateway_url, job_name='ai_factory_benchmark')
                    if success:
                        logger.info(f"  ✓ Metrics pushed to {pushgateway_url}")
                    else:
                        logger.warning(f"  ✗ Failed to push metrics to Pushgateway")
                except Exception as e:
                    logger.warning(f"  Failed to push metrics: {e}")
            
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
    parser.add_argument('--pushgateway', default=None,
                       help='Prometheus Pushgateway URL (e.g., http://mel2110:9091)')
    
    args = parser.parse_args()
    
    # Print enhanced banner
    print_banner()
    print_section("AI Factory Benchmarking Framework")
    
    # Show monitoring information
    print_monitoring_info()
    
    orchestrator = BenchmarkOrchestrator(args.recipe, pushgateway_url=args.pushgateway)
    
    try:
        report = orchestrator.run_benchmark()
        
        # Print enhanced results
        if report:
            print_section("Benchmark Results", style="bold green")
            print_benchmark_results(report)
            
            # Print completion banner
            report_path = f"reports/{orchestrator.benchmark_id}_report.json"
            print_completion_banner(orchestrator.benchmark_id, report_path)
        
    except Exception as e:
        print_error(f"Benchmark failed: {e}")
        raise


if __name__ == "__main__":
    main()
