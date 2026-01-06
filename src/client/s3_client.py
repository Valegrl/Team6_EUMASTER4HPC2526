#!/usr/bin/env python3
"""
S3/Object Storage Benchmark Client

Performs benchmarking operations against S3-compatible object storage.
Tests upload, download, list, and delete operations.
Runs on GPU-enabled nodes for optimal performance when co-located with GPU-accelerated workloads.
"""

import time
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional
from dataclasses import dataclass
import random
import string
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class S3RequestResult:
    """Result of an S3 operation"""
    timestamp: float
    duration: float
    success: bool
    operation_type: str
    bytes_transferred: int = 0
    error: Optional[str] = None


class S3BenchmarkClient:
    """Benchmark client for S3-compatible object storage
    
    Supports running on GPU-enabled nodes for:
    - Co-location with GPU-accelerated AI/ML workloads
    - Unified resource allocation in HPC environments
    - Efficient integration with GPU-based data processing pipelines
    
    Note: Standard MinIO/S3 does not natively use GPUs. This client runs on 
    GPU nodes to support integrated benchmarking of complete AI Factory stacks.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize S3 benchmark client
        
        Args:
            config: Configuration with S3 connection details
        """
        self.endpoint_url = config.get('endpoint_url', None)
        self.access_key = config.get('access_key', '')
        self.secret_key = config.get('secret_key', '')
        self.bucket_name = config.get('bucket_name', 'benchmark-bucket')
        self.region = config.get('region', 'us-east-1')
        self.operation_mix = config.get('operation_mix', {
            'put': 0.4,
            'get': 0.4,
            'list': 0.1,
            'delete': 0.1
        })
        self.object_sizes = config.get('object_sizes', {
            '1KB': 0.3,
            '10KB': 0.3,
            '100KB': 0.2,
            '1MB': 0.15,
            '10MB': 0.05
        })
        
        self.s3_client = None
        self.created_objects = []
        
        logger.info(f"Initialized S3 client for bucket: {self.bucket_name}")
    
    def connect(self):
        """Initialize S3 client"""
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
            logger.info("S3 client initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            return False
    
    def setup_bucket(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} exists")
        except ClientError:
            try:
                if self.region == 'us-east-1':
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                logger.info(f"Created bucket {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to create bucket: {e}")
                return False
        return True
    
    def _generate_random_data(self, size_bytes: int) -> bytes:
        """Generate random data of specified size"""
        return bytes(random.getrandbits(8) for _ in range(size_bytes))
    
    def _get_random_object_size(self) -> int:
        """Get random object size based on configured distribution"""
        rand = random.random()
        cumulative = 0
        
        size_map = {
            '1KB': 1024,
            '10KB': 10 * 1024,
            '100KB': 100 * 1024,
            '1MB': 1024 * 1024,
            '10MB': 10 * 1024 * 1024
        }
        
        for size_name, weight in self.object_sizes.items():
            cumulative += weight
            if rand <= cumulative:
                return size_map.get(size_name, 1024)
        
        return 1024  # Default to 1KB
    
    def execute_put(self) -> S3RequestResult:
        """Execute PUT operation (upload object)"""
        start_time = time.time()
        try:
            object_key = f"benchmark/{int(time.time() * 1000)}-{random.randint(1000, 9999)}.bin"
            size_bytes = self._get_random_object_size()
            data = self._generate_random_data(size_bytes)
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=data
            )
            
            self.created_objects.append(object_key)
            
            duration = time.time() - start_time
            return S3RequestResult(
                timestamp=start_time,
                duration=duration,
                success=True,
                operation_type='PUT',
                bytes_transferred=size_bytes
            )
        except Exception as e:
            duration = time.time() - start_time
            return S3RequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='PUT',
                error=str(e)
            )
    
    def execute_get(self) -> S3RequestResult:
        """Execute GET operation (download object)"""
        start_time = time.time()
        try:
            # Get a random object from created objects or list
            if self.created_objects:
                object_key = random.choice(self.created_objects)
            else:
                # List objects and pick one
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix='benchmark/',
                    MaxKeys=100
                )
                if 'Contents' in response and response['Contents']:
                    object_key = random.choice(response['Contents'])['Key']
                else:
                    # No objects to download, create one first
                    return self.execute_put()
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            data = response['Body'].read()
            size_bytes = len(data)
            
            duration = time.time() - start_time
            return S3RequestResult(
                timestamp=start_time,
                duration=duration,
                success=True,
                operation_type='GET',
                bytes_transferred=size_bytes
            )
        except Exception as e:
            duration = time.time() - start_time
            return S3RequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='GET',
                error=str(e)
            )
    
    def execute_list(self) -> S3RequestResult:
        """Execute LIST operation"""
        start_time = time.time()
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='benchmark/',
                MaxKeys=1000
            )
            
            object_count = len(response.get('Contents', []))
            
            duration = time.time() - start_time
            return S3RequestResult(
                timestamp=start_time,
                duration=duration,
                success=True,
                operation_type='LIST',
                bytes_transferred=object_count
            )
        except Exception as e:
            duration = time.time() - start_time
            return S3RequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='LIST',
                error=str(e)
            )
    
    def execute_delete(self) -> S3RequestResult:
        """Execute DELETE operation"""
        start_time = time.time()
        try:
            if self.created_objects:
                object_key = self.created_objects.pop(random.randrange(len(self.created_objects)))
            else:
                # List and delete a random object
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix='benchmark/',
                    MaxKeys=100
                )
                if 'Contents' in response and response['Contents']:
                    object_key = random.choice(response['Contents'])['Key']
                else:
                    # No objects to delete
                    duration = time.time() - start_time
                    return S3RequestResult(
                        timestamp=start_time,
                        duration=duration,
                        success=True,
                        operation_type='DELETE',
                        bytes_transferred=0
                    )
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            duration = time.time() - start_time
            return S3RequestResult(
                timestamp=start_time,
                duration=duration,
                success=True,
                operation_type='DELETE',
                bytes_transferred=0
            )
        except Exception as e:
            duration = time.time() - start_time
            return S3RequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='DELETE',
                error=str(e)
            )
    
    def execute_operation(self) -> S3RequestResult:
        """Execute a random operation based on operation_mix"""
        rand = random.random()
        cumulative = 0
        
        for operation, weight in self.operation_mix.items():
            cumulative += weight
            if rand <= cumulative:
                if operation == 'put':
                    return self.execute_put()
                elif operation == 'get':
                    return self.execute_get()
                elif operation == 'list':
                    return self.execute_list()
                elif operation == 'delete':
                    return self.execute_delete()
        
        # Default to put if something goes wrong
        return self.execute_put()
    
    def cleanup(self):
        """Clean up created objects"""
        logger.info(f"Cleaning up {len(self.created_objects)} objects...")
        for object_key in self.created_objects:
            try:
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=object_key
                )
            except Exception as e:
                logger.warning(f"Failed to delete {object_key}: {e}")
        self.created_objects.clear()
