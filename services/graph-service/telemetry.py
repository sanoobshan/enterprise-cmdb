"""
OpenTelemetry and Audit Logging Integration
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
import logging
import json
import requests
import os

logger = logging.getLogger(__name__)

class OpenTelemetrySetup:
    """Setup OpenTelemetry for distributed tracing"""
    
    @staticmethod
    def init():
        # Jaeger exporter for tracing
        jaeger_exporter = JaegerExporter(
            agent_host_name=os.getenv("JAEGER_HOST", "localhost"),
            agent_port=int(os.getenv("JAEGER_PORT", "6831")),
        )
        
        # Prometheus exporter for metrics
        prometheus_reader = PrometheusMetricReader()
        
        # Set up trace provider
        trace.set_tracer_provider(TracerProvider())
        trace.get_tracer_provider().add_span_processor(
            BatchSpanProcessor(jaeger_exporter)
        )
        
        # Set up metrics provider
        metrics.set_meter_provider(
            MeterProvider(metric_readers=[prometheus_reader])
        )
        
        logger.info("OpenTelemetry initialized")

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to capture and log all CMDB operations for audit trail"""
    
    def __init__(self, app, audit_service_url: str = "http://audit-logger:8002"):
        super().__init__(app)
        self.audit_service_url = audit_service_url
        self.tracer = trace.get_tracer(__name__)
    
    async def dispatch(self, request: Request, call_next):
        with self.tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
            # Get user info from headers
            user_id = request.headers.get("X-User-ID", "anonymous")
            user_email = request.headers.get("X-User-Email", "unknown@example.com")
            reason = request.headers.get("X-Access-Reason", "not-provided")
            octelium_session = request.headers.get("X-Octelium-Session", None)
            
            # Set span attributes
            span.set_attribute("user_id", user_id)
            span.set_attribute("method", request.method)
            span.set_attribute("path", request.url.path)
            span.set_attribute("reason", reason)
            
            # Process request
            response = await call_next(request)
            
            # Log audit event for write operations
            if request.method in ["POST", "PUT", "DELETE"]:
                asyncio.create_task(
                    self._log_audit(
                        request=request,
                        response=response,
                        user_id=user_id,
                        user_email=user_email,
                        reason=reason,
                        octelium_session=octelium_session
                    )
                )
            
            return response
    
    async def _log_audit(
        self, 
        request: Request, 
        response, 
        user_id: str, 
        user_email: str,
        reason: str,
        octelium_session: str
    ):
        """Send audit log to Audit Logger service"""
        try:
            # Determine action and resource from endpoint
            path = request.url.path
            method = request.method
            
            if "asset" in path:
                resource_type = "asset"
                if method == "POST":
                    action = "create"
                elif method == "PUT":
                    action = "update"
                elif method == "DELETE":
                    action = "delete"
                else:
                    action = "read"
                resource_id = path.split("/")[-1] if "/" in path else "unknown"
            
            elif "relationship" in path:
                resource_type = "relationship"
                action = "create" if method == "POST" else "update"
                resource_id = "unknown"
            
            else:
                resource_type = "unknown"
                action = method.lower()
                resource_id = path
            
            # Create audit log
            audit_log = {
                "user_id": user_id,
                "user_email": user_email,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "status": "success" if 200 <= response.status_code < 300 else "failure",
                "reason": reason,
                "details": {
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            # Send to audit logger
            headers = {}
            if octelium_session:
                headers["X-Octelium-Session"] = octelium_session
            
            response = requests.post(
                f"{self.audit_service_url}/audit",
                json=audit_log,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.debug(f"Audit log sent: {resource_type}/{resource_id}")
            else:
                logger.warning(f"Failed to send audit log: {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")

import asyncio
from datetime import datetime
