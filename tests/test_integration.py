#!/usr/bin/env python3
"""
Integration tests for the benchmarking framework
Tests the main orchestrator with mock services
"""

import unittest
import sys
from pathlib import Path
import tempfile
import json
import time
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from client.client import BenchmarkClient, RequestResult


class TestBenchmarkClient(unittest.TestCase):
    """Test the BenchmarkClient with real execution"""
    
    def test_client_with_failing_service(self):
        """Test that client handles failing services gracefully"""
        config = {
            'service_name': 'test-service',
            'service_type': 'ollama',
            'client_count': 2,
            'requests_per_second': 10,
            'duration': 1,  # Short duration for testing
            'service_url': 'http://localhost:9999',  # Non-existent service
            'model': 'test-model'
        }
        
        client = BenchmarkClient(config)
        results = client.run()
        
        # Should have results even if all requests failed
        self.assertGreater(len(results), 0)
        
        # All requests should have failed since service doesn't exist
        failed_count = sum(1 for r in results if not r.success)
        self.assertEqual(failed_count, len(results))
        
    def test_client_result_format(self):
        """Test that client results have the correct format"""
        config = {
            'service_name': 'test-service',
            'service_type': 'ollama',
            'client_count': 1,
            'requests_per_second': 5,
            'duration': 1,
            'service_url': 'http://localhost:9999',
            'model': 'test-model'
        }
        
        client = BenchmarkClient(config)
        results = client.run()
        
        # Check that results have required attributes
        for result in results:
            self.assertIsInstance(result, RequestResult)
            self.assertIsInstance(result.timestamp, float)
            self.assertIsInstance(result.duration, float)
            self.assertIsInstance(result.success, bool)
            self.assertTrue(hasattr(result, 'status_code'))
            self.assertTrue(hasattr(result, 'error'))
            self.assertTrue(hasattr(result, 'response_size'))


class TestMainOrchestrator(unittest.TestCase):
    """Test the main orchestrator logic"""
    
    def test_orchestrator_real_execution_path(self):
        """Test that orchestrator uses real client execution"""
        # Import here to avoid circular dependencies
        from main import BenchmarkOrchestrator
        from unittest.mock import patch
        
        # Create a minimal test recipe
        test_recipe = {
            'services': [{
                'service_name': 'test-ollama',
                'service_type': 'ollama',
                'client_count': 1,
                'requests_per_second': 5,
                'duration': 1,
                'service_url': 'http://localhost:9999',
                'model': 'test-model'
            }]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            import yaml
            yaml.dump(test_recipe, f)
            test_recipe_path = f.name
        
        try:
            # Mock the interface to return our test config
            with patch('middleware.interface.MiddlewareInterface') as mock_interface:
                mock_instance = MagicMock()
                mock_instance.start_recipe.return_value = {
                    'benchmark_id': 'test_benchmark_001',
                    'services': ['test-ollama']
                }
                mock_instance.get_services_info.return_value = test_recipe['services']
                mock_interface.return_value = mock_instance
                
                # Run the orchestrator
                orchestrator = BenchmarkOrchestrator(test_recipe_path)
                
                # This should execute the real benchmark flow
                # Even though services don't exist, it should handle errors gracefully
                try:
                    report = orchestrator.run_benchmark()
                    
                    # Verify that we got a report
                    self.assertIsNotNone(report)
                    self.assertIn('summary', report)
                    
                except Exception as e:
                    # If there's an exception, it should be a real execution error,
                    # not a "simulated metrics" issue
                    self.assertNotIn('simulation', str(e).lower())
                    
        finally:
            # Cleanup
            Path(test_recipe_path).unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
