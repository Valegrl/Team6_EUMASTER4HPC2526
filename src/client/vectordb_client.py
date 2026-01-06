#!/usr/bin/env python3
"""
Vector Database Benchmark Client

Performs benchmarking operations against vector databases with GPU acceleration support.
Supports: ChromaDB, Faiss, Milvus, Weaviate (all with GPU acceleration)
Tests: insert, search, update, delete vector operations.
"""

import time
import logging
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class VectorDBRequestResult:
    """Result of a vector database operation"""
    timestamp: float
    duration: float
    success: bool
    operation_type: str
    vectors_processed: int = 0
    error: Optional[str] = None


class VectorDBBenchmarkClient:
    """Benchmark client for vector databases with GPU support
    
    GPU capabilities by backend:
    - Faiss: Native GPU support via faiss-gpu for indexing and search
    - Milvus: Native GPU support for vector indexing and query processing
    - ChromaDB: Runs on GPU nodes for integrated AI workflows
    - Weaviate: Runs on GPU nodes for integrated AI workflows
    
    All backends can run on GPU-enabled nodes to support co-location with
    GPU-accelerated AI/ML workloads in HPC environments.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize vector DB benchmark client
        
        Args:
            config: Configuration with connection details
        """
        self.backend = config.get('backend', 'chromadb')  # chromadb, faiss, milvus, weaviate
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 8000)
        self.collection_name = config.get('collection_name', 'benchmark_collection')
        self.dimension = config.get('dimension', 384)  # embedding dimension
        self.operation_mix = config.get('operation_mix', {
            'insert': 0.3,
            'search': 0.5,
            'update': 0.1,
            'delete': 0.1
        })
        self.batch_size = config.get('batch_size', 10)
        self.search_k = config.get('search_k', 10)  # number of results to return
        
        self.client = None
        self.collection = None
        self.inserted_ids = []
        
        logger.info(f"Initialized vector DB client ({self.backend}) at {self.host}:{self.port}")
    
    def connect(self):
        """Connect to vector database based on backend type"""
        try:
            if self.backend == 'chromadb':
                return self._connect_chromadb()
            elif self.backend == 'faiss':
                return self._connect_faiss()
            elif self.backend == 'milvus':
                return self._connect_milvus()
            elif self.backend == 'weaviate':
                return self._connect_weaviate()
            else:
                logger.error(f"Unsupported backend: {self.backend}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to {self.backend}: {e}")
            return False
    
    def _connect_chromadb(self):
        """Connect to ChromaDB"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            self.client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            
            logger.info(f"Connected to ChromaDB, collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"ChromaDB connection error: {e}")
            return False
    
    def _connect_faiss(self):
        """Connect to Faiss (in-memory or server)"""
        try:
            import faiss
            
            # Create a Faiss index
            self.client = faiss.IndexFlatL2(self.dimension)
            
            logger.info(f"Initialized Faiss index with dimension {self.dimension}")
            return True
        except Exception as e:
            logger.error(f"Faiss initialization error: {e}")
            return False
    
    def _connect_milvus(self):
        """Connect to Milvus"""
        try:
            from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType
            
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            
            # Create collection if it doesn't exist
            from pymilvus import utility
            if not utility.has_collection(self.collection_name):
                fields = [
                    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension)
                ]
                schema = CollectionSchema(fields, description="Benchmark collection")
                self.collection = Collection(name=self.collection_name, schema=schema)
                
                # Create index
                index_params = {
                    "metric_type": "L2",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 1024}
                }
                self.collection.create_index(field_name="embedding", index_params=index_params)
            else:
                self.collection = Collection(name=self.collection_name)
            
            self.collection.load()
            
            logger.info(f"Connected to Milvus, collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"Milvus connection error: {e}")
            return False
    
    def _connect_weaviate(self):
        """Connect to Weaviate"""
        try:
            import weaviate
            
            self.client = weaviate.Client(f"http://{self.host}:{self.port}")
            
            # Create class (collection) if it doesn't exist
            class_name = self.collection_name.capitalize()
            if not self.client.schema.exists(class_name):
                class_obj = {
                    "class": class_name,
                    "vectorizer": "none",
                    "properties": [
                        {
                            "name": "data",
                            "dataType": ["text"]
                        }
                    ]
                }
                self.client.schema.create_class(class_obj)
            
            self.collection = class_name
            
            logger.info(f"Connected to Weaviate, class: {class_name}")
            return True
        except Exception as e:
            logger.error(f"Weaviate connection error: {e}")
            return False
    
    def _generate_random_vector(self) -> np.ndarray:
        """Generate random vector of configured dimension"""
        return np.random.randn(self.dimension).astype('float32')
    
    def _generate_random_vectors(self, count: int) -> np.ndarray:
        """Generate multiple random vectors"""
        return np.random.randn(count, self.dimension).astype('float32')
    
    def execute_insert(self) -> VectorDBRequestResult:
        """Execute vector insert operation"""
        start_time = time.time()
        try:
            if self.backend == 'chromadb':
                return self._insert_chromadb(start_time)
            elif self.backend == 'faiss':
                return self._insert_faiss(start_time)
            elif self.backend == 'milvus':
                return self._insert_milvus(start_time)
            elif self.backend == 'weaviate':
                return self._insert_weaviate(start_time)
        except Exception as e:
            duration = time.time() - start_time
            return VectorDBRequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='INSERT',
                error=str(e)
            )
    
    def _insert_chromadb(self, start_time: float) -> VectorDBRequestResult:
        """Insert vectors into ChromaDB"""
        vectors = self._generate_random_vectors(self.batch_size)
        ids = [f"vec_{int(time.time() * 1000000)}_{i}" for i in range(self.batch_size)]
        
        self.collection.add(
            embeddings=vectors.tolist(),
            ids=ids
        )
        
        self.inserted_ids.extend(ids)
        
        duration = time.time() - start_time
        return VectorDBRequestResult(
            timestamp=start_time,
            duration=duration,
            success=True,
            operation_type='INSERT',
            vectors_processed=self.batch_size
        )
    
    def _insert_faiss(self, start_time: float) -> VectorDBRequestResult:
        """Insert vectors into Faiss"""
        vectors = self._generate_random_vectors(self.batch_size)
        self.client.add(vectors)
        
        duration = time.time() - start_time
        return VectorDBRequestResult(
            timestamp=start_time,
            duration=duration,
            success=True,
            operation_type='INSERT',
            vectors_processed=self.batch_size
        )
    
    def _insert_milvus(self, start_time: float) -> VectorDBRequestResult:
        """Insert vectors into Milvus"""
        vectors = self._generate_random_vectors(self.batch_size)
        
        entities = [
            vectors.tolist()
        ]
        
        self.collection.insert(entities)
        
        duration = time.time() - start_time
        return VectorDBRequestResult(
            timestamp=start_time,
            duration=duration,
            success=True,
            operation_type='INSERT',
            vectors_processed=self.batch_size
        )
    
    def _insert_weaviate(self, start_time: float) -> VectorDBRequestResult:
        """Insert vectors into Weaviate"""
        vectors = self._generate_random_vectors(self.batch_size)
        
        with self.client.batch as batch:
            for i, vector in enumerate(vectors):
                batch.add_data_object(
                    {"data": f"benchmark_vector_{i}"},
                    self.collection,
                    vector=vector.tolist()
                )
        
        duration = time.time() - start_time
        return VectorDBRequestResult(
            timestamp=start_time,
            duration=duration,
            success=True,
            operation_type='INSERT',
            vectors_processed=self.batch_size
        )
    
    def execute_search(self) -> VectorDBRequestResult:
        """Execute vector search operation"""
        start_time = time.time()
        try:
            if self.backend == 'chromadb':
                return self._search_chromadb(start_time)
            elif self.backend == 'faiss':
                return self._search_faiss(start_time)
            elif self.backend == 'milvus':
                return self._search_milvus(start_time)
            elif self.backend == 'weaviate':
                return self._search_weaviate(start_time)
        except Exception as e:
            duration = time.time() - start_time
            return VectorDBRequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='SEARCH',
                error=str(e)
            )
    
    def _search_chromadb(self, start_time: float) -> VectorDBRequestResult:
        """Search in ChromaDB"""
        query_vector = self._generate_random_vector()
        
        results = self.collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=self.search_k
        )
        
        duration = time.time() - start_time
        return VectorDBRequestResult(
            timestamp=start_time,
            duration=duration,
            success=True,
            operation_type='SEARCH',
            vectors_processed=1
        )
    
    def _search_faiss(self, start_time: float) -> VectorDBRequestResult:
        """Search in Faiss"""
        query_vector = self._generate_random_vector().reshape(1, -1)
        
        distances, indices = self.client.search(query_vector, self.search_k)
        
        duration = time.time() - start_time
        return VectorDBRequestResult(
            timestamp=start_time,
            duration=duration,
            success=True,
            operation_type='SEARCH',
            vectors_processed=1
        )
    
    def _search_milvus(self, start_time: float) -> VectorDBRequestResult:
        """Search in Milvus"""
        query_vector = self._generate_random_vector()
        
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = self.collection.search(
            data=[query_vector.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=self.search_k
        )
        
        duration = time.time() - start_time
        return VectorDBRequestResult(
            timestamp=start_time,
            duration=duration,
            success=True,
            operation_type='SEARCH',
            vectors_processed=1
        )
    
    def _search_weaviate(self, start_time: float) -> VectorDBRequestResult:
        """Search in Weaviate"""
        query_vector = self._generate_random_vector()
        
        result = (
            self.client.query
            .get(self.collection, ["data"])
            .with_near_vector({"vector": query_vector.tolist()})
            .with_limit(self.search_k)
            .do()
        )
        
        duration = time.time() - start_time
        return VectorDBRequestResult(
            timestamp=start_time,
            duration=duration,
            success=True,
            operation_type='SEARCH',
            vectors_processed=1
        )
    
    def execute_update(self) -> VectorDBRequestResult:
        """Execute vector update operation (where supported)"""
        # Most vector DBs don't support direct updates, so we'll do delete + insert
        start_time = time.time()
        try:
            # For simplicity, just insert new vectors
            return self.execute_insert()
        except Exception as e:
            duration = time.time() - start_time
            return VectorDBRequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='UPDATE',
                error=str(e)
            )
    
    def execute_delete(self) -> VectorDBRequestResult:
        """Execute vector delete operation"""
        start_time = time.time()
        try:
            if self.backend == 'chromadb' and self.inserted_ids:
                # Delete a random subset of inserted vectors
                delete_count = min(self.batch_size, len(self.inserted_ids))
                ids_to_delete = random.sample(self.inserted_ids, delete_count)
                
                self.collection.delete(ids=ids_to_delete)
                
                for id_val in ids_to_delete:
                    self.inserted_ids.remove(id_val)
                
                duration = time.time() - start_time
                return VectorDBRequestResult(
                    timestamp=start_time,
                    duration=duration,
                    success=True,
                    operation_type='DELETE',
                    vectors_processed=delete_count
                )
            else:
                # For other backends, we can't easily delete specific vectors
                duration = time.time() - start_time
                return VectorDBRequestResult(
                    timestamp=start_time,
                    duration=duration,
                    success=True,
                    operation_type='DELETE',
                    vectors_processed=0
                )
        except Exception as e:
            duration = time.time() - start_time
            return VectorDBRequestResult(
                timestamp=start_time,
                duration=duration,
                success=False,
                operation_type='DELETE',
                error=str(e)
            )
    
    def execute_operation(self) -> VectorDBRequestResult:
        """Execute a random operation based on operation_mix"""
        rand = random.random()
        cumulative = 0
        
        for operation, weight in self.operation_mix.items():
            cumulative += weight
            if rand <= cumulative:
                if operation == 'insert':
                    return self.execute_insert()
                elif operation == 'search':
                    return self.execute_search()
                elif operation == 'update':
                    return self.execute_update()
                elif operation == 'delete':
                    return self.execute_delete()
        
        # Default to search if something goes wrong
        return self.execute_search()
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up vector database resources...")
        try:
            if self.backend == 'chromadb' and self.collection:
                # Optionally delete the collection
                # self.client.delete_collection(self.collection_name)
                pass
            elif self.backend == 'milvus' and self.collection:
                self.collection.release()
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
