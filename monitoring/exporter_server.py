#!/usr/bin/env python3
"""
Prometheus Metrics Exporter HTTP Server

This server exposes benchmark metrics in Prometheus format via HTTP endpoint.
It reads metrics from the SQLite database and serves them on /metrics endpoint.
"""

import sys
import time
import sqlite3
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import List, Dict, Any
import os
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetricsExporter:
    """Export benchmark metrics in Prometheus format from SQLite database"""
    
    def __init__(self, db_path: str = "metrics.db"):
        """
        Initialize the metrics exporter
        
        Args:
            db_path: Path to SQLite metrics database
        """
        self.db_path = db_path
        logger.info(f"Metrics exporter initialized with database: {db_path}")
    
    def get_latest_metrics(self, limit: int = 10000) -> List[Dict[str, Any]]:
        """
        Retrieve latest metrics from database
        
        Args:
            limit: Maximum number of metrics to retrieve
            
        Returns:
            List of metric dictionaries
        """
        try:
            if not Path(self.db_path).exists():
                logger.warning(f"Database {self.db_path} does not exist yet")
                return []
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get latest metrics
            cursor.execute('''
                SELECT benchmark_id, timestamp, service_name, client_id,
                       request_duration, success, status_code, 
                       error_message, response_size
                FROM metrics
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            metrics = []
            for row in rows:
                metrics.append({
                    'benchmark_id': row[0],
                    'timestamp': row[1],
                    'service_name': row[2],
                    'client_id': row[3],
                    'request_duration': row[4],
                    'success': bool(row[5]),
                    'status_code': row[6],
                    'error_message': row[7],
                    'response_size': row[8] or 0
                })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error retrieving metrics from database: {e}")
            return []
    
    def export_prometheus_format(self, metrics: List[Dict[str, Any]]) -> str:
        """
        Convert metrics to Prometheus exposition format
        
        Args:
            metrics: List of metric dictionaries
            
        Returns:
            Prometheus-formatted metrics string
        """
        if not metrics:
            return "# No metrics available\n"
        
        lines = []
        
        # Add header comments
        lines.append("# HELP benchmark_request_duration_seconds Request duration in seconds")
        lines.append("# TYPE benchmark_request_duration_seconds histogram")
        lines.append("")
        
        lines.append("# HELP benchmark_requests_total Total number of requests")
        lines.append("# TYPE benchmark_requests_total counter")
        lines.append("")
        
        lines.append("# HELP benchmark_requests_successful Successful requests")
        lines.append("# TYPE benchmark_requests_successful counter")
        lines.append("")
        
        lines.append("# HELP benchmark_requests_failed Failed requests")
        lines.append("# TYPE benchmark_requests_failed counter")
        lines.append("")
        
        lines.append("# HELP benchmark_response_size_bytes Response size in bytes")
        lines.append("# TYPE benchmark_response_size_bytes gauge")
        lines.append("")
        
        # Group metrics by service and benchmark_id
        service_metrics = {}
        for metric in metrics:
            service = metric.get('service_name', 'unknown')
            benchmark_id = metric.get('benchmark_id', 'unknown')
            key = f"{service}:{benchmark_id}"
            
            if key not in service_metrics:
                service_metrics[key] = {
                    'service': service,
                    'benchmark_id': benchmark_id,
                    'durations': [],
                    'total': 0,
                    'successful': 0,
                    'failed': 0,
                    'response_sizes': []
                }
            
            service_metrics[key]['total'] += 1
            service_metrics[key]['durations'].append(metric.get('request_duration', 0))
            
            if metric.get('success', False):
                service_metrics[key]['successful'] += 1
            else:
                service_metrics[key]['failed'] += 1
            
            if 'response_size' in metric and metric['response_size'] is not None:
                service_metrics[key]['response_sizes'].append(metric['response_size'])
        
        # Export metrics per service
        for key, stats in service_metrics.items():
            service = stats['service']
            benchmark_id = stats['benchmark_id']
            labels = f'service="{service}",benchmark_id="{benchmark_id}"'
            
            # Request counts
            lines.append(f'benchmark_requests_total{{{labels}}} {stats["total"]}')
            lines.append(f'benchmark_requests_successful{{{labels}}} {stats["successful"]}')
            lines.append(f'benchmark_requests_failed{{{labels}}} {stats["failed"]}')
            
            # Duration statistics
            durations = sorted(stats['durations'])
            if durations:
                total_duration = sum(durations)
                count = len(durations)
                
                lines.append(f'benchmark_request_duration_seconds_sum{{{labels}}} {total_duration}')
                lines.append(f'benchmark_request_duration_seconds_count{{{labels}}} {count}')
                
                # Create histogram buckets
                buckets = [0.001, 0.01, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
                for bucket in buckets:
                    count_in_bucket = sum(1 for d in durations if d <= bucket)
                    lines.append(
                        f'benchmark_request_duration_seconds_bucket{{le="{bucket}",{labels}}} {count_in_bucket}'
                    )
                
                # +Inf bucket
                lines.append(
                    f'benchmark_request_duration_seconds_bucket{{le="+Inf",{labels}}} {count}'
                )
            
            # Response sizes
            if stats['response_sizes']:
                avg_size = sum(stats['response_sizes']) / len(stats['response_sizes'])
                lines.append(f'benchmark_response_size_bytes{{{labels}}} {avg_size}')
            
            lines.append("")  # Empty line between services
        
        return "\n".join(lines)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for serving Prometheus metrics"""
    
    exporter = None  # Will be set by the server
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/metrics':
            self.serve_metrics()
        elif self.path == '/health':
            self.serve_health()
        else:
            self.send_error(404, "Not Found")
    
    def serve_metrics(self):
        """Serve Prometheus metrics"""
        try:
            metrics = self.exporter.get_latest_metrics()
            prometheus_output = self.exporter.export_prometheus_format(metrics)
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
            self.end_headers()
            self.wfile.write(prometheus_output.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error serving metrics: {e}")
            self.send_error(500, f"Internal Server Error: {e}")
    
    def serve_health(self):
        """Serve health check endpoint"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status": "healthy"}')
    
    def log_message(self, format, *args):
        """Custom log format"""
        logger.info("%s - %s" % (self.address_string(), format % args))


def run_server(port: int = 8080, db_path: str = "metrics.db"):
    """
    Run the metrics exporter HTTP server
    
    Args:
        port: Port to listen on
        db_path: Path to metrics database
    """
    # Create exporter instance
    exporter = MetricsExporter(db_path)
    
    # Set exporter in handler class
    MetricsHandler.exporter = exporter
    
    # Create and start server
    server_address = ('', port)
    httpd = HTTPServer(server_address, MetricsHandler)
    
    logger.info(f"Starting metrics exporter server on port {port}")
    logger.info(f"Metrics endpoint: http://0.0.0.0:{port}/metrics")
    logger.info(f"Health endpoint: http://0.0.0.0:{port}/health")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down metrics exporter server")
        httpd.shutdown()


if __name__ == '__main__':
    # Get configuration from environment variables
    port = int(os.getenv('EXPORTER_PORT', '8080'))
    db_path = os.getenv('METRICS_DB_PATH', '/app/metrics.db')
    
    run_server(port=port, db_path=db_path)
