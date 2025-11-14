#!/usr/bin/env python3
"""
Tests for the Metrics Interceptor component
"""

import sys
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from interceptor.interceptor import MetricsInterceptor


class TestMetricsInterceptor(unittest.TestCase):
    """Test cases for MetricsInterceptor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.interceptor = MetricsInterceptor('test-service')
    
    def test_initialization(self):
        """Test interceptor initialization"""
        self.assertEqual(self.interceptor.service_name, 'test-service')
        self.assertEqual(len(self.interceptor.metrics), 0)
    
    def test_record_metrics(self):
        """Test recording metrics"""
        self.interceptor.record_metrics(
            client_id='client-1',
            duration=0.5,
            success=True,
            status_code=200
        )
        
        self.assertEqual(len(self.interceptor.metrics), 1)
        metric = self.interceptor.metrics[0]
        self.assertEqual(metric.client_id, 'client-1')
        self.assertEqual(metric.request_duration, 0.5)
        self.assertTrue(metric.success)
        self.assertEqual(metric.status_code, 200)
    
    def test_get_metrics(self):
        """Test retrieving metrics"""
        # Record multiple metrics
        for i in range(5):
            self.interceptor.record_metrics(
                client_id=f'client-{i}',
                duration=0.1 * i,
                success=True,
                status_code=200
            )
        
        metrics = self.interceptor.get_metrics()
        self.assertEqual(len(metrics), 5)
        self.assertIsInstance(metrics, list)
        self.assertIsInstance(metrics[0], dict)
    
    def test_export_to_json(self):
        """Test exporting metrics to JSON"""
        self.interceptor.record_metrics(
            client_id='client-1',
            duration=0.5,
            success=True,
            status_code=200
        )
        
        # Get metrics as dict instead
        metrics = self.interceptor.get_metrics()
        self.assertIsInstance(metrics, list)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]['client_id'], 'client-1')


if __name__ == '__main__':
    unittest.main()
