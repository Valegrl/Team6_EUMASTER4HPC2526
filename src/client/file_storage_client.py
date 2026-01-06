#!/usr/bin/env python3
"""
File Storage Benchmark Client

Performs benchmarking operations against file storage systems.
Tests file I/O operations: read, write, seek, and metadata operations.
Runs on GPU-enabled nodes for optimal performance when co-located with GPU-accelerated workloads.
"""

import time
import logging
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import random
import string

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FileStorageRequestResult:
    """Result of a file storage operation"""
    timestamp: float
    duration: float
    success: bool
    operation_type: str
    bytes_transferred: int = 0
    error: Optional[str] = None


class FileStorageBenchmarkClient:
    """Benchmark client for file storage operations
    
    Supports running on GPU-enabled nodes for:
    - Co-location with GPU-accelerated AI/ML workloads
    - Unified resource allocation in HPC environments
    - Efficient data staging for GPU-based processing
    
    Note: Standard file storage does not natively use GPUs. This client runs on 
    GPU nodes to support integrated benchmarking of complete AI Factory stacks.
    Advanced configurations may leverage GPU-Direct Storage (GDS) when available.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize file storage benchmark client
        
        Args:
            config: Configuration with storage path and operation details
        """
        self.base_path = Path(config.get('base_path', '/tmp/benchmark_storage'))
        self.operation_mix = config.get('operation_mix', {
            'write': 0.4,
            'read': 0.4,
            'stat': 0.1,
            'delete': 0.1
        })
        self.file_sizes = config.get('file_sizes', {
            '1KB': 0.2,
            '10KB': 0.2,
            '100KB': 0.2,
            '1MB': 0.2,
            '10MB': 0.1,
            '100MB': 0.1
        })
        self.use_direct_io = config.get('use_direct_io', False)
        self.sync_mode = config.get('sync_mode', False)  # fsync after write
        
        self.created_files = []
        
        logger.info(f"Initialized file storage client at {self.base_path}")
    
    def setup(self):
        """Create benchmark directory structure"""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Storage path ready: {self.base_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create storage path: {e}")
            return False
    
    def _generate_random_data(self, size_bytes: int) -> bytes:
        """Generate random data of specified size"""
        return bytes(random.getrandbits(8) for _ in range(size_bytes))
    
    def _get_random_file_size(self) -> int:
        """Get random file size based on configured distribution"""
        rand = random.random()
        cumulative = 0
        
        size_map = {
            '1KB': 1024,
            '10KB': 10 * 1024,
            '100KB': 100 * 1024,
            '1MB': 1024 * 1024,
            '10MB': 10 * 1024 * 1024,
            '100MB': 100 * 1024 * 1024
        }
        
        for size_name, weight in self.file_sizes.items():
            cumulative += weight
            if rand <= cumulative:
                return size_map.get(size_name, 1024)
        
        return 1024  # Default to 1KB
    
    def execute_write(self) -> FileStorageRequestResult:
        """Execute file write operation"""
        start_time = time.time()
        try:
            filename = f"file_{int(time.time() * 1000)}_{random.randint(1000, 9999)}.bin"
            filepath = self.base_path / filename
            size_bytes = self._get_random_file_size()
            data = self._generate_random_data(size_bytes)
            
            # Write file
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            if self.use_direct_io and hasattr(os, 'O_DIRECT'):
                flags |= os.O_DIRECT
            
            fd = os.open(filepath, flags)
            try:
                os.write(fd, data)
                if self.sync_mode:
                    os.fsync(fd)
            finally:
                os.close(fd)
            
            self.created_files.append(filepath)
            
            duration = time.time() - start_time
            return FileStorageRequestResult(
                timestamp=start_time,
                duration=duration,
                success=True,
                operation_type='WRITE',
                bytes_transferred=size_bytes
            )
        except Exception as e:
            duration = time.time() - start_time
            return FileStorageRequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='WRITE',
                error=str(e)
            )
    
    def execute_read(self) -> FileStorageRequestResult:
        """Execute file read operation"""
        start_time = time.time()
        try:
            # Get a random file to read
            if self.created_files:
                filepath = random.choice(self.created_files)
            else:
                # List files and pick one
                files = list(self.base_path.glob('file_*.bin'))
                if files:
                    filepath = random.choice(files)
                else:
                    # No files to read, create one first
                    return self.execute_write()
            
            # Read file
            with open(filepath, 'rb') as f:
                data = f.read()
            
            size_bytes = len(data)
            
            duration = time.time() - start_time
            return FileStorageRequestResult(
                timestamp=start_time,
                duration=duration,
                success=True,
                operation_type='READ',
                bytes_transferred=size_bytes
            )
        except Exception as e:
            duration = time.time() - start_time
            return FileStorageRequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='READ',
                error=str(e)
            )
    
    def execute_stat(self) -> FileStorageRequestResult:
        """Execute file stat operation (metadata read)"""
        start_time = time.time()
        try:
            # Get a random file
            if self.created_files:
                filepath = random.choice(self.created_files)
            else:
                files = list(self.base_path.glob('file_*.bin'))
                if files:
                    filepath = random.choice(files)
                else:
                    return self.execute_write()
            
            # Get file stats
            stat_info = filepath.stat()
            size = stat_info.st_size
            
            duration = time.time() - start_time
            return FileStorageRequestResult(
                timestamp=start_time,
                duration=duration,
                success=True,
                operation_type='STAT',
                bytes_transferred=0
            )
        except Exception as e:
            duration = time.time() - start_time
            return FileStorageRequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='STAT',
                error=str(e)
            )
    
    def execute_delete(self) -> FileStorageRequestResult:
        """Execute file delete operation"""
        start_time = time.time()
        try:
            if self.created_files:
                filepath = self.created_files.pop(random.randrange(len(self.created_files)))
            else:
                files = list(self.base_path.glob('file_*.bin'))
                if files:
                    filepath = random.choice(files)
                else:
                    # No files to delete
                    duration = time.time() - start_time
                    return FileStorageRequestResult(
                        timestamp=start_time,
                        duration=duration,
                        success=True,
                        operation_type='DELETE',
                        bytes_transferred=0
                    )
            
            filepath.unlink()
            
            duration = time.time() - start_time
            return FileStorageRequestResult(
                timestamp=start_time,
                duration=duration,
                success=True,
                operation_type='DELETE',
                bytes_transferred=0
            )
        except Exception as e:
            duration = time.time() - start_time
            return FileStorageRequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='DELETE',
                error=str(e)
            )
    
    def execute_operation(self) -> FileStorageRequestResult:
        """Execute a random operation based on operation_mix"""
        rand = random.random()
        cumulative = 0
        
        for operation, weight in self.operation_mix.items():
            cumulative += weight
            if rand <= cumulative:
                if operation == 'write':
                    return self.execute_write()
                elif operation == 'read':
                    return self.execute_read()
                elif operation == 'stat':
                    return self.execute_stat()
                elif operation == 'delete':
                    return self.execute_delete()
        
        # Default to write if something goes wrong
        return self.execute_write()
    
    def cleanup(self):
        """Clean up created files"""
        logger.info(f"Cleaning up {len(self.created_files)} files...")
        for filepath in self.created_files:
            try:
                if filepath.exists():
                    filepath.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete {filepath}: {e}")
        self.created_files.clear()
        
        # Optionally remove the benchmark directory if empty
        try:
            if self.base_path.exists() and not any(self.base_path.iterdir()):
                self.base_path.rmdir()
        except Exception as e:
            logger.warning(f"Failed to remove directory: {e}")
