#!/usr/bin/env python3
"""
Prometheus Metrics Exporter for AI Factory Benchmarking Framework

Exports benchmark metrics in Prometheus text exposition format
for integration with Prometheus monitoring and Grafana dashboards.
"""

import sys
import time
from pathlib import Path
from typing import List, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitor.monitor import Monitor


class PrometheusExporter:
    """Export benchmark metrics in Prometheus format"""
    
    def __init__(self, monitor: Monitor):
        """
        Initialize the Prometheus exporter
        
        Args:
            monitor: Monitor instance with metrics data
        """
        self.monitor = monitor
    
    def export_metrics(self, output_file: str = None) -> str:
        """
        Export metrics in Prometheus text exposition format
        
        Args:
            output_file: Optional file path to write metrics
            
        Returns:
            Prometheus-formatted metrics string
        """
        metrics_data = self.monitor.get_data()
        
        # Build Prometheus metrics
        lines = []
        
        # Add header comments
        lines.append("# HELP benchmark_request_duration_seconds Request duration in seconds")
        lines.append("# TYPE benchmark_request_duration_seconds histogram")
        
        lines.append("# HELP benchmark_requests_total Total number of requests")
        lines.append("# TYPE benchmark_requests_total counter")
        
        lines.append("# HELP benchmark_requests_successful Successful requests")
        lines.append("# TYPE benchmark_requests_successful counter")
        
        lines.append("# HELP benchmark_requests_failed Failed requests")
        lines.append("# TYPE benchmark_requests_failed counter")
        
        lines.append("# HELP benchmark_response_size_bytes Response size in bytes")
        lines.append("# TYPE benchmark_response_size_bytes gauge")
        
        # Group metrics by service
        service_metrics = {}
        for metric in metrics_data:
            service = metric.get('service_name', 'unknown')
            if service not in service_metrics:
                service_metrics[service] = {
                    'durations': [],
                    'total': 0,
                    'successful': 0,
                    'failed': 0,
                    'response_sizes': []
                }
            
            service_metrics[service]['total'] += 1
            service_metrics[service]['durations'].append(metric.get('request_duration', 0))
            
            if metric.get('success', False):
                service_metrics[service]['successful'] += 1
            else:
                service_metrics[service]['failed'] += 1
            
            if 'response_size' in metric and metric['response_size'] is not None:
                service_metrics[service]['response_sizes'].append(metric['response_size'])
        
        # Export metrics per service
        for service, stats in service_metrics.items():
            labels = f'service="{service}",benchmark_id="{self.monitor.benchmark_id}"'
            
            # Request counts
            lines.append(f'benchmark_requests_total{{{labels}}} {stats["total"]}')
            lines.append(f'benchmark_requests_successful{{{labels}}} {stats["successful"]}')
            lines.append(f'benchmark_requests_failed{{{labels}}} {stats["failed"]}')
            
            # Duration histograms (simplified buckets)
            durations = sorted(stats['durations'])
            if durations:
                lines.append(f'benchmark_request_duration_seconds_sum{{{labels}}} {sum(durations)}')
                lines.append(f'benchmark_request_duration_seconds_count{{{labels}}} {len(durations)}')
                
                # Add histogram buckets
                buckets = [0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
                for bucket in buckets:
                    count = sum(1 for d in durations if d <= bucket)
                    lines.append(
                        f'benchmark_request_duration_seconds_bucket{{{labels},le="{bucket}"}} {count}'
                    )
                # +Inf bucket
                lines.append(
                    f'benchmark_request_duration_seconds_bucket{{{labels},le="+Inf"}} {len(durations)}'
                )
            
            # Response sizes
            if stats['response_sizes']:
                avg_size = sum(stats['response_sizes']) / len(stats['response_sizes'])
                lines.append(f'benchmark_response_size_bytes{{{labels}}} {avg_size}')
        
        prometheus_output = '\n'.join(lines) + '\n'
        
        # Write to file if specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(prometheus_output)
            print(f"Metrics exported to {output_file}")
        
        return prometheus_output
    
    def export_pushgateway_format(self, job_name: str = "benchmark") -> str:
        """
        Export metrics in format suitable for Prometheus Pushgateway
        
        Args:
            job_name: Job name for the pushgateway
            
        Returns:
            Pushgateway-formatted metrics
        """
        metrics = self.export_metrics()
        # Add job label to all metrics
        lines = []
        for line in metrics.split('\n'):
            if line and not line.startswith('#'):
                # Insert job label
                if '{' in line:
                    metric_name, rest = line.split('{', 1)
                    lines.append(f'{metric_name}{{job="{job_name}",{rest}')
                else:
                    lines.append(line)
            else:
                lines.append(line)
        
        return '\n'.join(lines)


def main():
    """Main entry point for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Export benchmark metrics in Prometheus format'
    )
    parser.add_argument('benchmark_id', help='Benchmark ID to export')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--db', default='metrics.db', help='Metrics database path')
    parser.add_argument('--pushgateway', action='store_true',
                       help='Format for Prometheus Pushgateway')
    
    args = parser.parse_args()
    
    # Load monitor with benchmark data
    monitor = Monitor(args.benchmark_id, args.db)
    
    # Create exporter
    exporter = PrometheusExporter(monitor)
    
    # Export metrics
    if args.pushgateway:
        output = exporter.export_pushgateway_format()
    else:
        output = exporter.export_metrics(args.output)
    
    if not args.output:
        print(output)


if __name__ == '__main__':
    main()
