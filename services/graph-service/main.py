"""
Graph Service - Core CMDB asset management
Integrated with Octelium for Zero Trust access and audit logging
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from pydantic import BaseModel
from typing import Optional, List
import os
import logging
from datetime import datetime
from telemetry import OpenTelemetrySetup, AuditLoggingMiddleware

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="Graph Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenTelemetry
OpenTelemetrySetup.init()

# Add audit logging middleware
app.add_middleware(
    AuditLoggingMiddleware,
    audit_service_url=os.getenv("AUDIT_SERVICE_URL", "http://localhost:8002")
)

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

# Pydantic models
class Asset(BaseModel):
    id: str
    type: str
    name: str
    properties: Optional[dict] = {}
    metadata: Optional[dict] = {}

class Relationship(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str
    properties: Optional[dict] = {}

@app.on_event("startup")
async def startup():
    """Initialize database schema"""
    logger.info("Initializing Neo4j schema...")
    with driver.session() as session:
        session.run("""
            CREATE CONSTRAINT IF NOT EXISTS FOR (a:Asset) REQUIRE a.id IS UNIQUE
        """)
    logger.info("Schema initialized")

@app.on_event("shutdown")
async def shutdown():
    """Close database connection"""
    driver.close()

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        with driver.session() as session:
            session.run("RETURN 1")
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Unhealthy")

@app.post("/asset")
async def create_asset(asset: Asset):
    """Create or update an asset"""
    try:
        with driver.session() as session:
            session.run("""
                MERGE (a:Asset {id: $id})
                SET a.type = $type,
                    a.name = $name,
                    a.properties = $properties,
                    a.metadata = $metadata,
                    a.updated_at = datetime()
            """, 
            id=asset.id,
            type=asset.type,
            name=asset.name,
            properties=asset.properties or {},
            metadata=asset.metadata or {}
            )
        logger.info(f"Asset created/updated: {asset.id}")
        return {"ok": True, "id": asset.id}
    except Exception as e:
        logger.error(f"Error creating asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/asset/{asset_id}")
async def get_asset(asset_id: str):
    """Get asset details"""
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (a:Asset {id: $id})
                RETURN a
            """, id=asset_id)
            
            record = result.single()
            if not record:
                raise HTTPException(status_code=404, detail="Asset not found")
            
            asset = record["a"]
            return {
                "id": asset["id"],
                "type": asset["type"],
                "name": asset["name"],
                "properties": asset.get("properties", {}),
                "metadata": asset.get("metadata", {}),
                "updated_at": asset.get("updated_at")
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/relationship")
async def create_relationship(rel: Relationship):
    """Create a relationship between assets"""
    try:
        with driver.session() as session:
            session.run("""
                MATCH (source:Asset {id: $source_id})
                MATCH (target:Asset {id: $target_id})
                MERGE (source)-[r:DEPENDS_ON {type: $rel_type}]->(target)
                SET r += $properties
            """,
            source_id=rel.source_id,
            target_id=rel.target_id,
            rel_type=rel.relationship_type,
            properties=rel.properties or {}
            )
        logger.info(f"Relationship created: {rel.source_id} -> {rel.target_id}")
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error creating relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/asset/{asset_id}")
async def delete_asset(asset_id: str):
    """Delete an asset"""
    try:
        with driver.session() as session:
            session.run("""
                MATCH (a:Asset {id: $id})
                DETACH DELETE a
            """, id=asset_id)
        logger.info(f"Asset deleted: {asset_id}")
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error deleting asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/assets")
async def list_assets(asset_type: Optional[str] = None, limit: int = 100):
    """List all assets with optional filtering"""
    try:
        with driver.session() as session:
            if asset_type:
                result = session.run("""
                    MATCH (a:Asset {type: $type})
                    RETURN a
                    LIMIT $limit
                """, type=asset_type, limit=limit)
            else:
                result = session.run("""
                    MATCH (a:Asset)
                    RETURN a
                    LIMIT $limit
                """, limit=limit)
            
            assets = []
            for record in result:
                asset = record["a"]
                assets.append({
                    "id": asset["id"],
                    "type": asset["type"],
                    "name": asset["name"],
                    "updated_at": asset.get("updated_at")
                })
            return {"assets": assets, "count": len(assets)}
    except Exception as e:
        logger.error(f"Error listing assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph/stats")
async def graph_stats():
    """Get graph statistics"""
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (a:Asset)
                RETURN count(a) as asset_count
            """)
            asset_count = result.single()[0]
            
            result = session.run("""
                MATCH ()-[r:DEPENDS_ON]->()
                RETURN count(r) as relationship_count
            """)
            relationship_count = result.single()[0]
            
            return {
                "assets": asset_count,
                "relationships": relationship_count,
                "timestamp": datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
