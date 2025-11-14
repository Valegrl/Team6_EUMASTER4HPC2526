#!/usr/bin/env python3
"""
Reporter Component
Generates reports and analysis from collected metrics
"""

import json
import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BenchmarkReporter:
    """Generates comprehensive reports from benchmark metrics"""
    
    def __init__(self, benchmark_id: str):
        """
        Initialize reporter
        
        Args:
            benchmark_id: Unique benchmark identifier
        """
        self.benchmark_id = benchmark_id
        
    def generate_report(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a comprehensive report from metrics
        
        Args:
            metrics: List of metric dictionaries
            
        Returns:
            Report dictionary with statistics and analysis
        """
        if not metrics:
            logger.warning("No metrics to generate report from")
            return {}
        
        # Separate by service
        services = {}
        for metric in metrics:
            service_name = metric.get('service_name', 'unknown')
            if service_name not in services:
                services[service_name] = []
            services[service_name].append(metric)
        
        # Generate report for each service
        service_reports = {}
        for service_name, service_metrics in services.items():
            service_reports[service_name] = self._analyze_service_metrics(service_metrics)
        
        # Global statistics
        all_durations = [m['request_duration'] for m in metrics if m.get('success')]
        
        report = {
            'benchmark_id': self.benchmark_id,
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_requests': len(metrics),
                'successful_requests': sum(1 for m in metrics if m.get('success')),
                'failed_requests': sum(1 for m in metrics if not m.get('success')),
                'success_rate': sum(1 for m in metrics if m.get('success')) / len(metrics) * 100,
                'avg_duration': statistics.mean(all_durations) if all_durations else 0,
                'median_duration': statistics.median(all_durations) if all_durations else 0,
                'min_duration': min(all_durations) if all_durations else 0,
                'max_duration': max(all_durations) if all_durations else 0,
                'stdev_duration': statistics.stdev(all_durations) if len(all_durations) > 1 else 0,
            },
            'services': service_reports
        }
        
        return report
    
    def _analyze_service_metrics(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze metrics for a specific service
        
        Args:
            metrics: List of metrics for a service
            
        Returns:
            Analysis dictionary
        """
        successful = [m for m in metrics if m.get('success')]
        failed = [m for m in metrics if not m.get('success')]
        
        durations = [m['request_duration'] for m in successful]
        
        # Calculate percentiles
        percentiles = {}
        if durations:
            sorted_durations = sorted(durations)
            percentiles = {
                'p50': self._percentile(sorted_durations, 50),
                'p90': self._percentile(sorted_durations, 90),
                'p95': self._percentile(sorted_durations, 95),
                'p99': self._percentile(sorted_durations, 99),
            }
        
        # Analyze by client
        clients = {}
        for metric in metrics:
            client_id = metric.get('client_id', 'unknown')
            if client_id not in clients:
                clients[client_id] = {'requests': 0, 'successful': 0, 'failed': 0}
            clients[client_id]['requests'] += 1
            if metric.get('success'):
                clients[client_id]['successful'] += 1
            else:
                clients[client_id]['failed'] += 1
        
        analysis = {
            'total_requests': len(metrics),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(metrics) * 100 if metrics else 0,
            'timing': {
                'avg_duration': statistics.mean(durations) if durations else 0,
                'median_duration': statistics.median(durations) if durations else 0,
                'min_duration': min(durations) if durations else 0,
                'max_duration': max(durations) if durations else 0,
                'stdev_duration': statistics.stdev(durations) if len(durations) > 1 else 0,
            },
            'percentiles': percentiles,
            'clients': clients,
            'throughput': self._calculate_throughput(metrics)
        }
        
        return analysis
    
    def _percentile(self, sorted_data: List[float], percentile: int) -> float:
        """
        Calculate percentile value
        
        Args:
            sorted_data: Sorted list of values
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Percentile value
        """
        if not sorted_data:
            return 0
        
        index = (len(sorted_data) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1
        
        if upper >= len(sorted_data):
            return sorted_data[-1]
        
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight
    
    def _calculate_throughput(self, metrics: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate throughput metrics
        
        Args:
            metrics: List of metrics
            
        Returns:
            Throughput statistics
        """
        if not metrics:
            return {'requests_per_second': 0}
        
        timestamps = [m['timestamp'] for m in metrics]
        duration = max(timestamps) - min(timestamps)
        
        return {
            'requests_per_second': len(metrics) / duration if duration > 0 else 0,
            'duration_seconds': duration
        }
    
    def save_report(self, report: Dict[str, Any], filepath: str = None):
        """
        Save report to file
        
        Args:
            report: Report dictionary
            filepath: Optional path to save report
        """
        if filepath is None:
            filepath = f"reports/{self.benchmark_id}_report.json"
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {filepath}")
    
    def generate_text_summary(self, report: Dict[str, Any]) -> str:
        """
        Generate a human-readable text summary of the report
        
        Args:
            report: Report dictionary
            
        Returns:
            Formatted text summary
        """
        summary = report.get('summary', {})
        
        text = f"""
Benchmark Report: {self.benchmark_id}
Generated: {report.get('generated_at', 'N/A')}
{'=' * 60}

Overall Summary:
  Total Requests:     {summary.get('total_requests', 0)}
  Successful:         {summary.get('successful_requests', 0)}
  Failed:             {summary.get('failed_requests', 0)}
  Success Rate:       {summary.get('success_rate', 0):.2f}%
  
Timing:
  Average Duration:   {summary.get('avg_duration', 0):.3f}s
  Median Duration:    {summary.get('median_duration', 0):.3f}s
  Min Duration:       {summary.get('min_duration', 0):.3f}s
  Max Duration:       {summary.get('max_duration', 0):.3f}s
  Std Dev:            {summary.get('stdev_duration', 0):.3f}s

Service Details:
"""
        
        for service_name, service_data in report.get('services', {}).items():
            text += f"\n  {service_name}:\n"
            text += f"    Requests: {service_data.get('total_requests', 0)}\n"
            text += f"    Success Rate: {service_data.get('success_rate', 0):.2f}%\n"
            
            timing = service_data.get('timing', {})
            text += f"    Avg Duration: {timing.get('avg_duration', 0):.3f}s\n"
            
            throughput = service_data.get('throughput', {})
            text += f"    Throughput: {throughput.get('requests_per_second', 0):.2f} req/s\n"
        
        return text


if __name__ == "__main__":
    # Example usage
    reporter = BenchmarkReporter("test_benchmark_001")
    
    # Simulate metrics
    test_metrics = [
        {
            'timestamp': 1000.0,
            'service_name': 'test-service',
            'client_id': 'client-1',
            'request_duration': 0.5,
            'success': True
        },
        {
            'timestamp': 1001.0,
            'service_name': 'test-service',
            'client_id': 'client-1',
            'request_duration': 0.7,
            'success': True
        }
    ]
    
    report = reporter.generate_report(test_metrics)
    print(reporter.generate_text_summary(report))
