#!/usr/bin/env python3
"""
PostgreSQL Benchmark Client

Performs benchmarking operations against PostgreSQL database servers.
Tests INSERT, SELECT, UPDATE, DELETE operations with various patterns.
Runs on GPU-enabled nodes for optimal performance when co-located with GPU-accelerated workloads.
"""

import time
import logging
import psycopg2
from psycopg2.extras import execute_batch
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import random
import string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PostgreSQLRequestResult:
    """Result of a PostgreSQL operation"""
    timestamp: float
    duration: float
    success: bool
    operation_type: str
    rows_affected: int = 0
    error: Optional[str] = None


class PostgreSQLBenchmarkClient:
    """Benchmark client for PostgreSQL database operations
    
    Supports running on GPU-enabled nodes for:
    - Co-location with GPU-accelerated AI/ML workloads
    - Unified resource allocation in HPC environments
    - Optimal performance when integrated with GPU-based analytics
    
    Note: Standard PostgreSQL does not natively use GPUs. This client runs on 
    GPU nodes to support integrated benchmarking of complete AI Factory stacks.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PostgreSQL benchmark client
        
        Args:
            config: Configuration with connection details
        """
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5432)
        self.database = config.get('database', 'benchmark')
        self.user = config.get('user', 'postgres')
        self.password = config.get('password', 'postgres')
        self.operation_mix = config.get('operation_mix', {
            'select': 0.4,
            'insert': 0.3,
            'update': 0.2,
            'delete': 0.1
        })
        self.batch_size = config.get('batch_size', 1)
        self.table_name = config.get('table_name', 'benchmark_test')
        
        self.connection = None
        
        logger.info(f"Initialized PostgreSQL client for {self.host}:{self.port}")
    
    def connect(self):
        """Establish connection to PostgreSQL"""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.connection.autocommit = True
            logger.info("Connected to PostgreSQL")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False
    
    def setup_test_table(self):
        """Create test table if it doesn't exist"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255),
                    value INTEGER,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_value ON {self.table_name}(value)')
            cursor.close()
            logger.info(f"Test table {self.table_name} ready")
            return True
        except Exception as e:
            logger.error(f"Failed to create test table: {e}")
            return False
    
    def execute_select(self) -> PostgreSQLRequestResult:
        """Execute SELECT query"""
        start_time = time.time()
        try:
            cursor = self.connection.cursor()
            value = random.randint(1, 10000)
            cursor.execute(
                f'SELECT * FROM {self.table_name} WHERE value = %s LIMIT 100',
                (value,)
            )
            rows = cursor.fetchall()
            cursor.close()
            
            duration = time.time() - start_time
            return PostgreSQLRequestResult(
                timestamp=start_time,
                duration=duration,
                success=True,
                operation_type='SELECT',
                rows_affected=len(rows)
            )
        except Exception as e:
            duration = time.time() - start_time
            return PostgreSQLRequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='SELECT',
                error=str(e)
            )
    
    def execute_insert(self) -> PostgreSQLRequestResult:
        """Execute INSERT operation"""
        start_time = time.time()
        try:
            cursor = self.connection.cursor()
            name = ''.join(random.choices(string.ascii_letters, k=10))
            value = random.randint(1, 10000)
            data = ''.join(random.choices(string.ascii_letters + string.digits, k=100))
            
            cursor.execute(
                f'INSERT INTO {self.table_name} (name, value, data) VALUES (%s, %s, %s)',
                (name, value, data)
            )
            cursor.close()
            
            duration = time.time() - start_time
            return PostgreSQLRequestResult(
                timestamp=start_time,
                duration=duration,
                success=True,
                operation_type='INSERT',
                rows_affected=1
            )
        except Exception as e:
            duration = time.time() - start_time
            return PostgreSQLRequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='INSERT',
                error=str(e)
            )
    
    def execute_update(self) -> PostgreSQLRequestResult:
        """Execute UPDATE operation"""
        start_time = time.time()
        try:
            cursor = self.connection.cursor()
            value = random.randint(1, 10000)
            new_data = ''.join(random.choices(string.ascii_letters + string.digits, k=100))
            
            cursor.execute(
                f'UPDATE {self.table_name} SET data = %s WHERE value = %s',
                (new_data, value)
            )
            rows_affected = cursor.rowcount
            cursor.close()
            
            duration = time.time() - start_time
            return PostgreSQLRequestResult(
                timestamp=start_time,
                duration=duration,
                success=True,
                operation_type='UPDATE',
                rows_affected=rows_affected
            )
        except Exception as e:
            duration = time.time() - start_time
            return PostgreSQLRequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='UPDATE',
                error=str(e)
            )
    
    def execute_delete(self) -> PostgreSQLRequestResult:
        """Execute DELETE operation"""
        start_time = time.time()
        try:
            cursor = self.connection.cursor()
            value = random.randint(1, 10000)
            
            cursor.execute(
                f'DELETE FROM {self.table_name} WHERE value = %s LIMIT 10',
                (value,)
            )
            rows_affected = cursor.rowcount
            cursor.close()
            
            duration = time.time() - start_time
            return PostgreSQLRequestResult(
                timestamp=start_time,
                duration=duration,
                success=True,
                operation_type='DELETE',
                rows_affected=rows_affected
            )
        except Exception as e:
            duration = time.time() - start_time
            return PostgreSQLRequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='DELETE',
                error=str(e)
            )
    
    def execute_operation(self) -> PostgreSQLRequestResult:
        """Execute a random operation based on operation_mix"""
        rand = random.random()
        cumulative = 0
        
        for operation, weight in self.operation_mix.items():
            cumulative += weight
            if rand <= cumulative:
                if operation == 'select':
                    return self.execute_select()
                elif operation == 'insert':
                    return self.execute_insert()
                elif operation == 'update':
                    return self.execute_update()
                elif operation == 'delete':
                    return self.execute_delete()
        
        # Default to select if something goes wrong
        return self.execute_select()
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL connection closed")
