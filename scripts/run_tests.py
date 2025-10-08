#!/usr/bin/env python3
"""
Test Runner for AI Factory Benchmarking Framework
Run all unit tests and generate a report
"""

import sys
import unittest
from pathlib import Path
import time

def run_tests():
    """Run all unit tests"""
    print("=" * 70)
    print("AI Factory Benchmarking Framework - Test Suite")
    print("=" * 70)
    print()
    
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent.parent / 'tests'
    suite = loader.discover(str(start_dir), pattern='test_*.py')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    # Print summary
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Duration: {end_time - start_time:.2f}s")
    print()
    
    # Exit code
    if result.wasSuccessful():
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests())
