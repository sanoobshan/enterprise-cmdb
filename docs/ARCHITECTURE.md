# Enterprise CMDB Platform - Architecture Documentation

## System Overview

Enterprise CMDB Platform is an event-driven, graph-based configuration management database designed for modern cloud-native infrastructure.

### Key Characteristics
- **Event-Driven**: Real-time asset updates through Kafka
- **Graph-Based**: Neo4j for relationship modeling
- **Cloud-Native**: Kubernetes-first design
- **Scalable**: Microservices architecture
- **Policy-Driven**: OPA for compliance enforcement

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Systems                          │
│        (Kubernetes, VMs, Cloud Providers, Config Sources)       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                    Events Feed
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐   ┌─────▼────┐  ┌──────▼───┐
    │K8s      │   │VM Agent  │  │API Events│
    │Controller    │          │  │Publisher │
    └────┬────┘   └─────┬────┘  └──────┬───┘
         │               │               │
         └───────────────┼───────────────┘
                    Kafka Bus
                    ┌────┴────┐
         ┌──────────▼─────────▼──────────┐
         │    Event Ingestor Service     │
         │  (Normalization & Enrichment)  │
         └──────────┬─────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
    ┌───▼───┐  ┌───▼───┐  ┌───▼────┐
    │Graph  │  │Drift  │  │ Impact │
    │Service│  │Engine │  │Engine  │
    └───┬───┘  └───┬───┘  └───┬────┘
        │          │          │
        └──────────┴──────────┘
                │
          Neo4j Graph DB
                │
        ┌───────┴────────┐
        │                │
    ┌───▼────┐      ┌───▼──────┐
    │API     │      │WebUI     │
    │Portal  │      │Dashboard │
    └────────┘      └──────────┘
```

---

## Core Components

### 1. Graph Service
**Purpose**: Central asset and relationship management

**Technology Stack**:
- FastAPI
- Neo4j
- Python 3.11

**Responsibilities**:
- Store assets (pods, nodes, services, databases, etc.)
- Manage relationships (depends_on, contains, runs_on, etc.)
- Provide RESTful API for asset CRUD
- Index and optimize graph queries

**Key Endpoints**:
```
POST   /asset                 # Create/update asset
GET    /asset/{id}            # Get asset details
GET    /assets                # List assets
DELETE /asset/{id}            # Delete asset
POST   /relationship          # Create relationship
GET    /graph/stats           # Graph statistics
```

---

### 2. Event Ingestor
**Purpose**: Consumes events and normalizes them into assets

**Technology Stack**:
- Kafka Consumer
- Python 3.11

**Event Types**:
- `ASSET_DISCOVERED`: New resource found
- `ASSET_DELETED`: Resource removed
- `ASSET_UPDATED`: Configuration changed
- `CONFIG_DRIFT`: Configuration mismatch detected

**Flow**:
```
Event → Kafka → Consumer → Normalize → Graph Service
```

---

### 3. Kubernetes Controller
**Purpose**: Auto-discovers Kubernetes resources

**Watches**:
- Pods (containers)
- Nodes (compute)
- Services (networking)
- Deployments (orchestration)

**Publishes Events**:
- Pod creation/deletion
- Node status changes
- Service updates

---

### 4. Drift Engine
**Purpose**: Detects configuration drift

**Detection Logic**:
```
Actual Config Hash ≠ Desired Config Hash → Drift Alert
```

**Algorithms**:
- SHA256 hashing for config comparison
- Recursive property diffing
- Change tracking

---

### 5. Impact Engine
**Purpose**: Analyzes dependency impact

**Capabilities**:
- Upstream dependency analysis
- Downstream impact assessment
- Change risk scoring
- Path finding

**Queries**:
```cypher
MATCH (a:Asset {id: $id})<-[:DEPENDS_ON*]-(affected)
RETURN affected
```

---

## Data Model

### Asset Node
```json
{
  "id": "pod/default/nginx-123",
  "type": "pod",
  "name": "nginx-123",
  "namespace": "default",
  "properties": {
    "image": "nginx:latest",
    "replicas": 1,
    "resources": {
      "cpu": "500m",
      "memory": "512Mi"
    }
  },
  "metadata": {
    "created_at": "2026-02-05T10:00:00Z",
    "updated_at": "2026-02-05T10:00:00Z",
    "source": "k8s-controller"
  }
}
```

### Relationships
```
Pod -[RUNS_ON]-> Node
Pod -[DEPENDS_ON]-> Service
Service -[DEPENDS_ON]-> Database
Deployment -[CONTAINS]-> Pod
```

---

## Event Flow

### Asset Discovery
```
1. K8s Controller watches for new pods
2. Pod created in cluster
3. Controller publishes ASSET_DISCOVERED event
4. Event → Kafka (cmdb-events topic)
5. Event Ingestor consumes event
6. Graph Service creates Asset node
7. Dashboard updated in real-time
```

### Configuration Change
```
1. User updates pod configuration
2. K8s controller detects change
3. ASSET_UPDATED event published
4. Drift Engine receives event
5. Compares actual vs desired config
6. If mismatch → CONFIG_DRIFT event
7. Alert system notifies teams
```

### Impact Analysis
```
1. User requests impact for asset X
2. Impact Engine queries graph
3. Finds all dependent assets
4. Calculates impact depth
5. Assigns risk level
6. Returns impact analysis
```

---

## Technology Stack

### Core Services
- **Python 3.11**: Primary language
- **FastAPI**: RESTful APIs
- **Uvicorn**: ASGI server

### Data & Messaging
- **Neo4j 5**: Graph database
- **Kafka**: Event streaming
- **PostgreSQL**: Optional relational data
- **Zookeeper**: Kafka coordination

### Deployment
- **Docker**: Containerization
- **Kubernetes**: Orchestration
- **Helm**: Package management
- **ArgoCD**: GitOps

### Monitoring & Security
- **Prometheus**: Metrics
- **Grafana**: Dashboards
- **OPA**: Policy enforcement
- **NetworkPolicy**: Security

---

## Scaling Strategies

### Horizontal Scaling
```
Graph Service:       2+ replicas (stateless)
Event Ingestor:      3+ instances (distributed)
Kafka:               3+ brokers (multi-partition topics)
Neo4j:               Read replicas (Neo4j Enterprise)
```

### Vertical Scaling
```
Neo4j:      Increase heap size, cache
Kafka:      More CPU, network I/O
Services:   Resource limits based on load
```

### Performance Optimizations
```
- Neo4j query caching
- Kafka partitioning (by asset type)
- Event batching
- Graph indexing
- Connection pooling
```

---

## Security Architecture

### Network Security
```
NetworkPolicy:
- Pod-to-pod: Allow within namespace
- Ingress:    Restricted to frontend
- Egress:     Allow to databases, Kafka
```

### Authentication & Authorization
```
- RBAC for Kubernetes
- Service accounts per component
- Sealed secrets for credentials
- API key management
```

### Policy Enforcement
```
OPA/Rego:
- Public DB detection
- Encryption requirements
- Resource limits
- Compliance checks
```

---

## Disaster Recovery

### Backup Strategy
```
Neo4j:
- Daily full backup
- WAL (Write-Ahead Logs)
- Cloud storage replication
- Recovery time: < 1 hour

Kafka:
- 3-node cluster
- Replication factor: 3
- Topic retention: 7 days
```

### High Availability
```
- Multiple replicas per service
- Load balancing
- Circuit breakers
- Health checks
```

---

## Monitoring & Observability

### Metrics
```
Graph Service:
- API response time
- Database queries/sec
- Asset count
- Relationship count

Event Ingestor:
- Events processed/sec
- Processing latency
- Error rate

Drift Engine:
- Drift detection rate
- Alert latency
```

### Logging
```
- Structured JSON logs
- Centralized log aggregation
- Audit trail for changes
- Error tracking
```

### Alerting
```
Prometheus Rules:
- High event processing latency
- Database connection failures
- Service pod crashes
- Resource exhaustion
```

---

## Deployment Topology

### Local Development
```
docker-compose up
- All services in containers
- Shared network
- Persistent volumes
```

### Kubernetes Production
```
Namespace: cmdb
Services:
  - graph-service (2 replicas)
  - event-ingestor (3 replicas)
  - drift-engine (2 replicas)
  - impact-engine (2 replicas)
  - k8s-controller (1 replica)
  
Infrastructure:
  - Neo4j (3 nodes)
  - Kafka (3 brokers)
  - PostgreSQL (1 master, 1 replica)
  - Prometheus, Grafana
```

---

## API Specification

See API.md for detailed endpoint documentation.

---

## Future Enhancements

1. **ML Integration**
   - Anomaly detection
   - Predictive analytics
   - Automated remediation

2. **Multi-Cloud**
   - AWS, Azure, GCP adapters
   - Hybrid cloud support

3. **Advanced Features**
   - Scenario planning
   - What-if analysis
   - Automated optimization

4. **Integrations**
   - Backstage plugin
   - ServiceNow connector
   - Custom webhooks

---

## References

- Neo4j Documentation: https://neo4j.com/docs/
- Kubernetes API: https://kubernetes.io/docs/
- Kafka Architecture: https://kafka.apache.org/documentation/
- OPA/Rego: https://www.openpolicyagent.org/docs/
