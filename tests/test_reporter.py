#!/usr/bin/env python3
"""
Tests for the Reporter component
"""

import sys
import os
import unittest
from pathlib import Path
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from reporter.reporter import BenchmarkReporter


class TestReporter(unittest.TestCase):
    """Test cases for BenchmarkReporter"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.reporter = BenchmarkReporter('test_benchmark')
        
        # Sample metrics data with proper timestamp format
        import time
        timestamp = time.time()
        self.metrics = [
            {
                'service_name': 'test-service',
                'client_id': 'client-1',
                'request_duration': 0.5,
                'success': True,
                'status_code': 200,
                'timestamp': timestamp,
                'response_size': 1024
            },
            {
                'service_name': 'test-service',
                'client_id': 'client-2',
                'request_duration': 0.7,
                'success': True,
                'status_code': 200,
                'timestamp': timestamp + 1,
                'response_size': 2048
            },
            {
                'service_name': 'test-service',
                'client_id': 'client-1',
                'request_duration': 1.0,
                'success': False,
                'status_code': 500,
                'timestamp': timestamp + 2,
                'response_size': 0
            }
        ]
    
    def test_generate_report(self):
        """Test report generation"""
        report = self.reporter.generate_report(self.metrics)
        
        self.assertEqual(report['benchmark_id'], 'test_benchmark')
        self.assertIn('summary', report)
        self.assertIn('services', report)
        self.assertIn('generated_at', report)
    
    def test_summary_statistics(self):
        """Test summary statistics"""
        report = self.reporter.generate_report(self.metrics)
        summary = report['summary']
        
        self.assertEqual(summary['total_requests'], 3)
        self.assertEqual(summary['successful_requests'], 2)
        self.assertEqual(summary['failed_requests'], 1)
        self.assertAlmostEqual(summary['success_rate'], 66.67, places=1)
    
    def test_service_breakdown(self):
        """Test service-level breakdown"""
        report = self.reporter.generate_report(self.metrics)
        
        self.assertIn('test-service', report['services'])
        service_stats = report['services']['test-service']
        
        self.assertEqual(service_stats['total_requests'], 3)
        self.assertEqual(service_stats['successful'], 2)
        self.assertEqual(service_stats['failed'], 1)
    
    def test_percentile_calculation(self):
        """Test percentile calculations"""
        report = self.reporter.generate_report(self.metrics)
        service_stats = report['services']['test-service']
        
        self.assertIn('percentiles', service_stats)
        percentiles = service_stats['percentiles']
        
        self.assertIn('p50', percentiles)
        self.assertIn('p90', percentiles)
        self.assertIn('p95', percentiles)
        self.assertIn('p99', percentiles)
    
    def test_text_summary_generation(self):
        """Test text summary generation"""
        report = self.reporter.generate_report(self.metrics)
        text_summary = self.reporter.generate_text_summary(report)
        
        self.assertIsInstance(text_summary, str)
        self.assertIn('test_benchmark', text_summary)
        self.assertIn('Total Requests', text_summary)
        self.assertIn('Success Rate', text_summary)
    
    def test_save_report(self):
        """Test saving report to file"""
        report = self.reporter.generate_report(self.metrics)
        
        # Save report
        self.reporter.save_report(report)
        
        # Verify file exists
        report_file = Path('reports') / f'{self.reporter.benchmark_id}_report.json'
        self.assertTrue(report_file.exists())
        
        # Cleanup
        if report_file.exists():
            report_file.unlink()


if __name__ == '__main__':
    unittest.main()
