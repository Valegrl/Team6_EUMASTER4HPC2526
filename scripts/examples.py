#!/usr/bin/env python3
"""
Example usage of the benchmarking framework components
This demonstrates how each component works independently
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

print("=" * 60)
print("AI Factory Benchmarking Framework - Component Examples")
print("=" * 60)

# Example 1: Middleware Interface
print("\n1. Middleware Interface Example")
print("-" * 60)
from middleware.interface import MiddlewareInterface

interface = MiddlewareInterface('recipe.yml')
result = interface.start_recipe()
print(f"Started benchmark: {result['benchmark_id']}")
print(f"Services: {len(result['services'])}")

services = interface.get_services_info()
for service in services[:2]:  # Show first 2 services
    print(f"  - {service['service_name']}: {service['client_count']} clients, "
          f"{service['requests_per_second']} req/s")

# Example 2: Logger
print("\n2. Logger Example")
print("-" * 60)
from logger.logger import BenchmarkLogger

logger = BenchmarkLogger("example_benchmark_001")
logger.log_benchmark_start({'services': ['ollama']})
logger.log_request('ollama', 'client-1', {'prompt': 'Hello'})
logger.log_response('ollama', 'client-1', True, 0.5, 200)
print("Logged requests and responses")

# Example 3: Metrics Interceptor
print("\n3. Metrics Interceptor Example")
print("-" * 60)
from interceptor.interceptor import MetricsInterceptor

interceptor = MetricsInterceptor('example-service')
for i in range(5):
    interceptor.record_metrics(
        client_id=f"client-{i % 2}",
        duration=0.5 + (i * 0.1),
        success=True,
        status_code=200
    )
print(f"Collected {len(interceptor.metrics)} metrics")
print(f"First metric: duration={interceptor.metrics[0].request_duration}s")

# Example 4: Monitor
print("\n4. Monitor Example")
print("-" * 60)
from monitor.monitor import Monitor

monitor = Monitor("example_benchmark_001", "example_metrics.db")
metrics = interceptor.get_metrics()
monitor.record_metrics('example-service', metrics)
print(f"Stored {len(metrics)} metrics in database")

retrieved = monitor.get_data()
print(f"Retrieved {len(retrieved)} metrics from database")

# Example 5: Reporter
print("\n5. Reporter Example")
print("-" * 60)
from reporter.reporter import BenchmarkReporter

reporter = BenchmarkReporter("example_benchmark_001")
report = reporter.generate_report(retrieved)
print(f"Generated report with {report['summary']['total_requests']} total requests")
print(f"Success rate: {report['summary']['success_rate']:.2f}%")
print(f"Average duration: {report['summary']['avg_duration']:.3f}s")

# Show text summary
print("\nReport Summary:")
print(reporter.generate_text_summary(report))

# Example 6: Service Manager
print("\n6. Service Manager Example")
print("-" * 60)
from server.server import ServiceManager

service_config = {
    'service_name': 'example-ollama',
    'container_image': 'docker://ollama/ollama',
    'service_type': 'ollama',
    'port': 11434,
    'slurm': {
        'partition': 'gpu',
        'time': '00:30:00'
    }
}

manager = ServiceManager(service_config)
manager.start_service()
status = manager.get_service_status()
print(f"Service status: {status['status']}")
print(f"Container image: {status['container_image']}")

print("\n" + "=" * 60)
print("All component examples completed successfully!")
print("=" * 60)

# Cleanup
import os
if os.path.exists("example_metrics.db"):
    os.remove("example_metrics.db")
    print("\nCleaned up example database")
