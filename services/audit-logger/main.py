"""
Audit Logger Service - Tracks WHO, WHAT, WHEN, WHY for CMDB operations
Integrates with Octelium for Zero Trust access control
"""

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional, List
import os
import logging
from datetime import datetime
import json
import requests

# OpenTelemetry setup
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cmdb:password@localhost:5432/cmdb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# OpenTelemetry setup
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)
tracer = trace.get_tracer(__name__)

app = FastAPI(title="Audit Logger Service", version="1.0.0")

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)
SQLAlchemyInstrumentor().instrument(engine_or_connection=engine)
RequestsInstrumentor().instrument()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database models
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String, index=True)
    user_email = Column(String)
    action = Column(String, index=True)
    resource_type = Column(String, index=True)
    resource_id = Column(String, index=True)
    status = Column(String)
    reason = Column(Text)
    details = Column(JSON)
    ip_address = Column(String)
    user_agent = Column(String)
    octelium_session_id = Column(String)

Base.metadata.create_all(bind=engine)

# Pydantic models
class AuditLogCreate(BaseModel):
    user_id: str
    user_email: str
    action: str  # create, read, update, delete, access
    resource_type: str  # asset, relationship, policy
    resource_id: str
    status: str  # success, failure
    reason: Optional[str] = None  # why they accessed it
    details: Optional[dict] = None

class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    user_id: str
    user_email: str
    action: str
    resource_type: str
    resource_id: str
    status: str
    reason: Optional[str]
    details: Optional[dict]
    ip_address: str
    user_agent: Optional[str]
    
    class Config:
        from_attributes = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
async def startup():
    """Verify database connection"""
    logger.info("Audit Logger Service starting...")
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        logger.info("Connected to PostgreSQL")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/audit")
async def create_audit_log(
    log: AuditLogCreate,
    request: Request,
    db: Session = None,
    x_user_id: str = Header(None),
    x_octelium_session: str = Header(None)
):
    """
    Create an audit log entry
    
    Tracks:
    - WHO: user_id, user_email
    - WHAT: action, resource_type, resource_id
    - WHEN: timestamp (automatic)
    - WHY: reason field
    """
    if not db:
        db = SessionLocal()
    
    with tracer.start_as_current_span("create_audit_log") as span:
        try:
            # Get client info
            ip_address = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent")
            
            # Create audit record
            db_log = AuditLog(
                user_id=log.user_id,
                user_email=log.user_email,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                status=log.status,
                reason=log.reason,
                details=log.details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                octelium_session_id=x_octelium_session
            )
            
            db.add(db_log)
            db.commit()
            db.refresh(db_log)
            
            # Span attributes for observability
            span.set_attribute("user_id", log.user_id)
            span.set_attribute("action", log.action)
            span.set_attribute("resource_id", log.resource_id)
            span.set_attribute("reason", log.reason)
            
            logger.info(
                f"Audit log created - User: {log.user_id}, "
                f"Action: {log.action}, Resource: {log.resource_id}, "
                f"Reason: {log.reason}"
            )
            
            return AuditLogResponse.from_orm(db_log)
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating audit log: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/user/{user_id}")
async def get_user_audit_logs(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = None
):
    """Get all audit logs for a specific user"""
    if not db:
        db = SessionLocal()
    
    logs = db.query(AuditLog)\
        .filter(AuditLog.user_id == user_id)\
        .order_by(AuditLog.timestamp.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()
    
    return {
        "user_id": user_id,
        "logs": [AuditLogResponse.from_orm(log) for log in logs],
        "count": len(logs)
    }

@app.get("/audit/resource/{resource_type}/{resource_id}")
async def get_resource_audit_logs(
    resource_type: str,
    resource_id: str,
    limit: int = 100,
    db: Session = None
):
    """Get all audit logs for a specific resource"""
    if not db:
        db = SessionLocal()
    
    logs = db.query(AuditLog)\
        .filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id
        )\
        .order_by(AuditLog.timestamp.desc())\
        .limit(limit)\
        .all()
    
    return {
        "resource": f"{resource_type}/{resource_id}",
        "logs": [AuditLogResponse.from_orm(log) for log in logs],
        "count": len(logs)
    }

@app.get("/audit/action/{action}")
async def get_action_audit_logs(
    action: str,
    limit: int = 100,
    offset: int = 0,
    db: Session = None
):
    """
    Get audit logs by action type
    
    Actions:
    - create: Asset/relationship created
    - read: Asset/relationship accessed
    - update: Asset/relationship modified
    - delete: Asset/relationship removed
    - access: User accessed the system
    """
    if not db:
        db = SessionLocal()
    
    logs = db.query(AuditLog)\
        .filter(AuditLog.action == action)\
        .order_by(AuditLog.timestamp.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()
    
    return {
        "action": action,
        "logs": [AuditLogResponse.from_orm(log) for log in logs],
        "count": len(logs)
    }

@app.get("/audit/reason/{reason}")
async def get_logs_by_reason(
    reason: str,
    limit: int = 50,
    db: Session = None
):
    """
    Find all access logs with a specific reason
    
    Examples:
    - "troubleshooting": investigating issues
    - "incident-response": responding to incident
    - "maintenance": planned maintenance
    - "investigation": security investigation
    - "routine": routine operations
    """
    if not db:
        db = SessionLocal()
    
    logs = db.query(AuditLog)\
        .filter(AuditLog.reason.ilike(f"%{reason}%"))\
        .order_by(AuditLog.timestamp.desc())\
        .limit(limit)\
        .all()
    
    return {
        "reason": reason,
        "logs": [AuditLogResponse.from_orm(log) for log in logs],
        "count": len(logs)
    }

@app.get("/audit/timeline/{resource_type}/{resource_id}")
async def get_resource_timeline(
    resource_type: str,
    resource_id: str,
    db: Session = None
):
    """Get complete audit timeline for a resource (WHO, WHAT, WHEN, WHY)"""
    if not db:
        db = SessionLocal()
    
    logs = db.query(AuditLog)\
        .filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id
        )\
        .order_by(AuditLog.timestamp.asc())\
        .all()
    
    timeline = []
    for log in logs:
        timeline.append({
            "timestamp": log.timestamp.isoformat(),
            "who": {
                "user_id": log.user_id,
                "email": log.user_email,
                "ip": log.ip_address
            },
            "what": {
                "action": log.action,
                "status": log.status
            },
            "when": log.timestamp.isoformat(),
            "why": log.reason,
            "details": log.details
        })
    
    return {
        "resource": f"{resource_type}/{resource_id}",
        "timeline": timeline,
        "total_changes": len(timeline)
    }

@app.get("/audit/compliance-report")
async def compliance_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = None
):
    """Generate compliance report of all audit logs"""
    if not db:
        db = SessionLocal()
    
    query = db.query(AuditLog)
    
    if start_date:
        query = query.filter(AuditLog.timestamp >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(AuditLog.timestamp <= datetime.fromisoformat(end_date))
    
    logs = query.all()
    
    # Generate statistics
    actions = {}
    users = {}
    resources = {}
    statuses = {}
    
    for log in logs:
        actions[log.action] = actions.get(log.action, 0) + 1
        users[log.user_id] = users.get(log.user_id, 0) + 1
        resources[log.resource_type] = resources.get(log.resource_type, 0) + 1
        statuses[log.status] = statuses.get(log.status, 0) + 1
    
    return {
        "report_date": datetime.utcnow().isoformat(),
        "total_events": len(logs),
        "by_action": actions,
        "by_user": users,
        "by_resource_type": resources,
        "by_status": statuses,
        "events": [AuditLogResponse.from_orm(log) for log in logs[:100]]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
