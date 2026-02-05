"""
Impact Engine - Analyzes asset dependencies and impact
"""

from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase
from pydantic import BaseModel
from typing import Optional, List
import os
import logging
from datetime import datetime
import networkx as nx

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

app = FastAPI(title="Impact Engine", version="1.0.0")

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

class ImpactAnalysis(BaseModel):
    asset_id: str
    affected_assets: List[str]
    impact_depth: int
    risk_level: str

@app.on_event("startup")
async def startup():
    """Verify database connection"""
    logger.info("Impact Engine starting up...")
    try:
        with driver.session() as session:
            session.run("RETURN 1")
        logger.info("Connected to Neo4j")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise

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

@app.get("/impact/{asset_id}")
async def get_impact(asset_id: str, depth: int = 5):
    """
    Get impact analysis for an asset
    Shows which assets depend on this asset (downstream impact)
    """
    try:
        with driver.session() as session:
            # Get all assets that depend on the given asset (upstream dependencies)
            result = session.run("""
                MATCH (a:Asset {id: $asset_id})<-[:DEPENDS_ON*..10]-(affected:Asset)
                RETURN DISTINCT affected.id as affected_id, 
                       LENGTH(p) as distance
                ORDER BY distance
            """, asset_id=asset_id)
            
            affected_assets = []
            max_depth = 0
            for record in result:
                affected_id = record["affected_id"]
                distance = record["distance"]
                affected_assets.append({
                    "id": affected_id,
                    "distance": distance
                })
                max_depth = max(max_depth, distance)
            
            # Determine risk level based on impact
            if len(affected_assets) > 10:
                risk_level = "CRITICAL"
            elif len(affected_assets) > 5:
                risk_level = "HIGH"
            elif len(affected_assets) > 1:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            return {
                "asset_id": asset_id,
                "affected_assets": affected_assets,
                "impact_count": len(affected_assets),
                "max_depth": max_depth,
                "risk_level": risk_level,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    except Exception as e:
        logger.error(f"Error analyzing impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dependencies/{asset_id}")
async def get_dependencies(asset_id: str, depth: int = 5):
    """
    Get dependencies for an asset
    Shows which assets this asset depends on (upstream dependencies)
    """
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (a:Asset {id: $asset_id})-[:DEPENDS_ON*..10]->(dep:Asset)
                RETURN DISTINCT dep.id as dep_id, 
                       dep.type as type,
                       LENGTH(p) as distance
                ORDER BY distance
            """, asset_id=asset_id)
            
            dependencies = []
            for record in result:
                dependencies.append({
                    "id": record["dep_id"],
                    "type": record["type"],
                    "distance": record["distance"]
                })
            
            return {
                "asset_id": asset_id,
                "dependencies": dependencies,
                "dependency_count": len(dependencies),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    except Exception as e:
        logger.error(f"Error getting dependencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/path/{source_id}/{target_id}")
async def get_dependency_path(source_id: str, target_id: str):
    """
    Find the dependency path between two assets
    """
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH path = (source:Asset {id: $source_id})-[:DEPENDS_ON*]->(target:Asset {id: $target_id})
                RETURN [node in nodes(path) | node.id] as path,
                       length(path) - 1 as hops
                LIMIT 1
            """, source_id=source_id, target_id=target_id)
            
            record = result.single()
            if not record:
                return {
                    "connected": False,
                    "source": source_id,
                    "target": target_id
                }
            
            return {
                "connected": True,
                "source": source_id,
                "target": target_id,
                "path": record["path"],
                "hops": record["hops"],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    except Exception as e:
        logger.error(f"Error finding path: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/change-impact")
async def assess_change_impact(asset_id: str, change_type: str = "update"):
    """
    Assess the potential impact of making changes to an asset
    """
    try:
        with driver.session() as session:
            # Get all dependent assets
            result = session.run("""
                MATCH (a:Asset {id: $asset_id})<-[:DEPENDS_ON*]-(affected:Asset)
                RETURN DISTINCT affected.id as affected_id,
                       affected.type as type
            """, asset_id=asset_id)
            
            affected_assets = []
            for record in result:
                affected_assets.append({
                    "id": record["affected_id"],
                    "type": record["type"]
                })
            
            # Risk assessment
            assessment = {
                "asset_id": asset_id,
                "change_type": change_type,
                "affected_count": len(affected_assets),
                "affected_assets": affected_assets,
                "recommendation": ""
            }
            
            if len(affected_assets) == 0:
                assessment["recommendation"] = "SAFE - No dependent assets"
                assessment["risk_score"] = 0
            elif len(affected_assets) <= 2:
                assessment["recommendation"] = "LOW RISK - Few dependent assets"
                assessment["risk_score"] = 2
            elif len(affected_assets) <= 5:
                assessment["recommendation"] = "MEDIUM RISK - Several dependent assets"
                assessment["risk_score"] = 5
            else:
                assessment["recommendation"] = "HIGH RISK - Many dependent assets, consider maintenance window"
                assessment["risk_score"] = 8
            
            assessment["timestamp"] = datetime.utcnow().isoformat()
            
            return assessment
    
    except Exception as e:
        logger.error(f"Error assessing change impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph/topology")
async def get_topology():
    """
    Get the full dependency graph topology
    """
    try:
        with driver.session() as session:
            # Get all nodes
            result = session.run("""
                MATCH (a:Asset)
                RETURN a.id as id, a.type as type, a.name as name
            """)
            
            nodes = []
            for record in result:
                nodes.append({
                    "id": record["id"],
                    "type": record["type"],
                    "name": record["name"]
                })
            
            # Get all relationships
            result = session.run("""
                MATCH (source:Asset)-[r:DEPENDS_ON]->(target:Asset)
                RETURN source.id as source_id,
                       target.id as target_id,
                       type(r) as relationship_type
            """)
            
            edges = []
            for record in result:
                edges.append({
                    "source": record["source_id"],
                    "target": record["target_id"],
                    "type": record["relationship_type"]
                })
            
            return {
                "nodes": nodes,
                "edges": edges,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    except Exception as e:
        logger.error(f"Error getting topology: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
