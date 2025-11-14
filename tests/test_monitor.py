#!/usr/bin/env python3
"""
Tests for the Monitor component
"""

import sys
import os
import unittest
from pathlib import Path
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from monitor.monitor import Monitor


class TestMonitor(unittest.TestCase):
    """Test cases for Monitor"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Use temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.monitor = Monitor('test_benchmark', self.temp_db.name)
    
    def tearDown(self):
        """Clean up test resources"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_initialization(self):
        """Test monitor initialization"""
        self.assertEqual(self.monitor.benchmark_id, 'test_benchmark')
        self.assertTrue(os.path.exists(self.temp_db.name))
    
    def test_record_metrics(self):
        """Test recording metrics"""
        metrics = [
            {
                'service_name': 'test-service',
                'client_id': 'client-1',
                'request_duration': 0.5,
                'success': True,
                'status_code': 200,
                'timestamp': '2025-10-22T10:00:00',
                'response_size': 1024
            }
        ]
        
        self.monitor.record_metrics('test-service', metrics)
        
        # Retrieve and verify
        retrieved = self.monitor.get_data()
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0]['service_name'], 'test-service')
        self.assertEqual(retrieved[0]['client_id'], 'client-1')
    
    def test_get_all_data(self):
        """Test retrieving all metrics data"""
        # Record metrics for multiple services
        for service in ['service-1', 'service-2']:
            metrics = [
                {
                    'service_name': service,
                    'client_id': 'client-1',
                    'request_duration': 0.5,
                    'success': True,
                    'status_code': 200,
                    'timestamp': '2025-10-22T10:00:00',
                    'response_size': 1024
                }
            ]
            self.monitor.record_metrics(service, metrics)
        
        # Get all data
        all_data = self.monitor.get_data()
        self.assertEqual(len(all_data), 2)
        service_names = [m['service_name'] for m in all_data]
        self.assertIn('service-1', service_names)
        self.assertIn('service-2', service_names)
    
    def test_multiple_metrics(self):
        """Test recording multiple metrics"""
        metrics = [
            {
                'service_name': 'test-service',
                'client_id': f'client-{i}',
                'request_duration': 0.1 * i,
                'success': True,
                'status_code': 200,
                'timestamp': '2025-10-22T10:00:00',
                'response_size': 1024 * i
            }
            for i in range(10)
        ]
        
        self.monitor.record_metrics('test-service', metrics)
        
        retrieved = self.monitor.get_data()
        self.assertEqual(len(retrieved), 10)


if __name__ == '__main__':
    unittest.main()
