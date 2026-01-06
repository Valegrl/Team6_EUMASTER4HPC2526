#!/usr/bin/env python3
"""
Interceptor/Middleware Component
Intercepts requests and collects metrics
"""

import time
import logging
from typing import Dict, Any, Callable, List
from dataclasses import dataclass, asdict
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MetricData:
    """Data structure for a single metric measurement"""
    timestamp: float
    service_name: str
    request_duration: float
    success: bool
    client_id: str
    status_code: int = None
    error_message: str = None
    response_size: int = 0


class MetricsInterceptor:
    """Intercepts and records metrics from client requests"""
    
    def __init__(self, service_name: str):
        """
        Initialize metrics interceptor
        
        Args:
            service_name: Name of the service being monitored
        """
        self.service_name = service_name
        self.metrics: List[MetricData] = []
        
    def record_metrics(self, 
                      client_id: str,
                      duration: float,
                      success: bool,
                      status_code: int = None,
                      error: str = None,
                      response_size: int = 0) -> MetricData:
        """
        Record metrics for a request
        
        Args:
            client_id: Identifier of the client making the request
            duration: Request duration in seconds
            success: Whether the request was successful
            status_code: HTTP status code
            error: Error message if request failed
            response_size: Size of the response in bytes
            
        Returns:
            MetricData object
        """
        metric = MetricData(
            timestamp=time.time(),
            service_name=self.service_name,
            request_duration=duration,
            success=success,
            client_id=client_id,
            status_code=status_code,
            error_message=error,
            response_size=response_size
        )
        
        self.metrics.append(metric)
        logger.debug(f"Recorded metric: {metric}")
        return metric
    
    def get_metrics(self) -> List[Dict[str, Any]]:
        """
        Get all collected metrics
        
        Returns:
            List of metrics as dictionaries
        """
        metrics_list = [asdict(m) for m in self.metrics]
        # Ensure all metrics have service_name for Prometheus compatibility
        for metric in metrics_list:
            if 'service_name' not in metric or not metric['service_name']:
                metric['service_name'] = self.service_name
        return metrics_list
    
    def get_client_metrics(self, client_id: str) -> List[Dict[str, Any]]:
        """
        Get metrics for a specific client
        
        Args:
            client_id: Client identifier
            
        Returns:
            List of metrics for the specified client
        """
        return [asdict(m) for m in self.metrics if m.client_id == client_id]
    
    def export_metrics(self, filepath: str):
        """
        Export metrics to a JSON file
        
        Args:
            filepath: Path to save the metrics
        """
        with open(filepath, 'w') as f:
            json.dump(self.get_metrics(), f, indent=2)
        logger.info(f"Exported {len(self.metrics)} metrics to {filepath}")
    
    def clear_metrics(self):
        """Clear all collected metrics"""
        self.metrics.clear()
        logger.info("Metrics cleared")


class InterceptorMiddleware:
    """Middleware that intercepts requests and forwards them while collecting metrics"""
    
    def __init__(self, service_name: str):
        """
        Initialize interceptor middleware
        
        Args:
            service_name: Name of the service
        """
        self.interceptor = MetricsInterceptor(service_name)
        
    def intercept_request(self, 
                         request_func: Callable,
                         client_id: str,
                         *args, **kwargs) -> Any:
        """
        Intercept a request, collect metrics, and forward it
        
        Args:
            request_func: The function that makes the actual request
            client_id: Client identifier
            *args, **kwargs: Arguments to pass to request_func
            
        Returns:
            Result from request_func
        """
        start_time = time.time()
        
        try:
            result = request_func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Record metrics
            self.interceptor.record_metrics(
                client_id=client_id,
                duration=duration,
                success=True,
                status_code=getattr(result, 'status_code', None),
                response_size=getattr(result, 'response_size', 0)
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record failure metrics
            self.interceptor.record_metrics(
                client_id=client_id,
                duration=duration,
                success=False,
                error=str(e)
            )
            
            raise
    
    def get_all_metrics(self) -> List[Dict[str, Any]]:
        """Get all collected metrics"""
        return self.interceptor.get_metrics()


if __name__ == "__main__":
    # Example usage
    interceptor = MetricsInterceptor("test-service")
    interceptor.record_metrics("client-1", 0.5, True, 200, response_size=1024)
    interceptor.record_metrics("client-1", 0.7, True, 200, response_size=2048)
    print(f"Collected {len(interceptor.metrics)} metrics")
    print(interceptor.get_metrics())
