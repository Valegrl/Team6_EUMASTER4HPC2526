#!/usr/bin/env python3
"""
Monitor Component
Collects, stores, and manages metrics from benchmarking runs
"""

import json
import logging
import time
from typing import Dict, Any, List
from pathlib import Path
import sqlite3
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricStorage:
    """Stores metrics in a SQLite database"""
    
    def __init__(self, db_path: str = "metrics.db"):
        """
        Initialize metric storage
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
        self.benchmark_id = None  # Will be set by Monitor
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                benchmark_id TEXT,
                timestamp REAL,
                service_name TEXT,
                client_id TEXT,
                request_duration REAL,
                success INTEGER,
                status_code INTEGER,
                error_message TEXT,
                response_size INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_benchmark_id 
            ON metrics(benchmark_id)
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def store_metric(self, benchmark_id: str, metric: Dict[str, Any]):
        """
        Store a single metric
        
        Args:
            benchmark_id: Benchmark identifier
            metric: Metric data dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO metrics 
            (benchmark_id, timestamp, service_name, client_id, request_duration, 
             success, status_code, error_message, response_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            benchmark_id,
            metric.get('timestamp', time.time()),
            metric.get('service_name'),
            metric.get('client_id'),
            metric.get('request_duration'),
            1 if metric.get('success') else 0,
            metric.get('status_code'),
            metric.get('error_message'),
            metric.get('response_size', 0)
        ))
        
        conn.commit()
        conn.close()
    
    def store_metrics_batch(self, benchmark_id: str, metrics: List[Dict[str, Any]]):
        """
        Store multiple metrics in a batch
        
        Args:
            benchmark_id: Benchmark identifier
            metrics: List of metric dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for metric in metrics:
            cursor.execute('''
                INSERT INTO metrics 
                (benchmark_id, timestamp, service_name, client_id, request_duration, 
                 success, status_code, error_message, response_size)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                benchmark_id,
                metric.get('timestamp', time.time()),
                metric.get('service_name'),
                metric.get('client_id'),
                metric.get('request_duration'),
                1 if metric.get('success') else 0,
                metric.get('status_code'),
                metric.get('error_message'),
                metric.get('response_size', 0)
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Stored {len(metrics)} metrics for benchmark {benchmark_id}")
    
    def get_metrics(self, benchmark_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all metrics for a benchmark
        
        Args:
            benchmark_id: Benchmark identifier
            
        Returns:
            List of metric dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, service_name, client_id, request_duration, 
                   success, status_code, error_message, response_size
            FROM metrics
            WHERE benchmark_id = ?
            ORDER BY timestamp
        ''', (benchmark_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        metrics = []
        for row in rows:
            metrics.append({
                'timestamp': row[0],
                'service_name': row[1],
                'client_id': row[2],
                'request_duration': row[3],
                'success': bool(row[4]),
                'status_code': row[5],
                'error_message': row[6],
                'response_size': row[7]
            })
        
        return metrics


class Monitor:
    """Main monitor component for collecting and managing metrics"""
    
    def __init__(self, benchmark_id: str, storage_path: str = "metrics.db"):
        """
        Initialize monitor
        
        Args:
            benchmark_id: Unique benchmark identifier
            storage_path: Path to metrics database
        """
        self.benchmark_id = benchmark_id
        self.storage = MetricStorage(storage_path)
        
    def record_metrics(self, service_name: str, metrics: List[Dict[str, Any]]):
        """
        Record metrics from a service
        
        Args:
            service_name: Name of the service
            metrics: List of metric data
        """
        # Add service name to metrics if not present
        for metric in metrics:
            if 'service_name' not in metric:
                metric['service_name'] = service_name
        
        self.storage.store_metrics_batch(self.benchmark_id, metrics)
        logger.info(f"Recorded {len(metrics)} metrics for {service_name}")
    
    def get_data(self, benchmark_id: str = None) -> List[Dict[str, Any]]:
        """
        Get raw metric data
        
        Args:
            benchmark_id: Optional specific benchmark ID, defaults to current
            
        Returns:
            List of metric dictionaries
        """
        bid = benchmark_id or self.benchmark_id
        return self.storage.get_metrics(bid)
    
    def export_raw_data(self, filepath: str):
        """
        Export raw metrics to JSON file
        
        Args:
            filepath: Path to export file
        """
        metrics = self.get_data()
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump({
                'benchmark_id': self.benchmark_id,
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics
            }, f, indent=2)
        
        logger.info(f"Exported {len(metrics)} metrics to {filepath}")


if __name__ == "__main__":
    # Example usage
    monitor = Monitor("test_benchmark_001")
    
    # Simulate some metrics
    test_metrics = [
        {
            'client_id': 'client-1',
            'request_duration': 0.5,
            'success': True,
            'status_code': 200,
            'response_size': 1024
        },
        {
            'client_id': 'client-1',
            'request_duration': 0.7,
            'success': True,
            'status_code': 200,
            'response_size': 2048
        }
    ]
    
    monitor.record_metrics('test-service', test_metrics)
    data = monitor.get_data()
    print(f"Retrieved {len(data)} metrics")
