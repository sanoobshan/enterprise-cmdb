# Enterprise CMDB Platform - API Documentation

## Base URLs

- **Local**: `http://localhost:8000` (Graph Service)
- **Local**: `http://localhost:8001` (Impact Engine)
- **Production**: `https://api.cmdb.example.com`

---

## Authentication

Currently uses service-to-service authentication via Kubernetes service accounts. Future versions will support:
- API Keys
- OAuth 2.0
- JWT tokens

---

## Graph Service API (Port 8000)

### Health Check
```http
GET /health
```

**Response**: `200 OK`
```json
{
  "status": "healthy"
}
```

---

### Create/Update Asset
```http
POST /asset
Content-Type: application/json

{
  "id": "pod/default/nginx-123",
  "type": "pod",
  "name": "nginx-123",
  "properties": {
    "image": "nginx:latest",
    "namespace": "default"
  },
  "metadata": {
    "source": "k8s-controller"
  }
}
```

**Response**: `200 OK`
```json
{
  "ok": true,
  "id": "pod/default/nginx-123"
}
```

---

### Get Asset
```http
GET /asset/{asset_id}
```

**Example**:
```
GET /asset/pod/default/nginx-123
```

**Response**: `200 OK`
```json
{
  "id": "pod/default/nginx-123",
  "type": "pod",
  "name": "nginx-123",
  "properties": {
    "image": "nginx:latest",
    "namespace": "default"
  },
  "metadata": {
    "source": "k8s-controller"
  },
  "updated_at": "2026-02-05T10:00:00Z"
}
```

**Error Responses**:
- `404 Not Found`: Asset doesn't exist
- `500 Internal Server Error`: Database error

---

### List Assets
```http
GET /assets?asset_type=pod&limit=100
```

**Query Parameters**:
- `asset_type` (optional): Filter by asset type
- `limit` (optional, default: 100): Maximum results

**Response**: `200 OK`
```json
{
  "assets": [
    {
      "id": "pod/default/nginx-123",
      "type": "pod",
      "name": "nginx-123",
      "updated_at": "2026-02-05T10:00:00Z"
    },
    {
      "id": "pod/default/app-456",
      "type": "pod",
      "name": "app-456",
      "updated_at": "2026-02-05T09:55:00Z"
    }
  ],
  "count": 2
}
```

---

### Delete Asset
```http
DELETE /asset/{asset_id}
```

**Example**:
```
DELETE /asset/pod/default/nginx-123
```

**Response**: `200 OK`
```json
{
  "ok": true
}
```

---

### Create Relationship
```http
POST /relationship
Content-Type: application/json

{
  "source_id": "pod/default/nginx-123",
  "target_id": "node/worker-1",
  "relationship_type": "RUNS_ON",
  "properties": {
    "since": "2026-02-05T10:00:00Z"
  }
}
```

**Response**: `200 OK`
```json
{
  "ok": true
}
```

---

### Graph Statistics
```http
GET /graph/stats
```

**Response**: `200 OK`
```json
{
  "assets": 1542,
  "relationships": 3201,
  "timestamp": "2026-02-05T10:00:00Z"
}
```

---

## Impact Engine API (Port 8001)

### Health Check
```http
GET /health
```

---

### Get Impact Analysis
```http
GET /impact/{asset_id}?depth=5
```

**Query Parameters**:
- `depth` (optional, default: 5): Maximum relationship depth

**Example**:
```
GET /impact/pod/default/database-1
```

**Response**: `200 OK`
```json
{
  "asset_id": "pod/default/database-1",
  "affected_assets": [
    {
      "id": "pod/default/app-service-1",
      "distance": 1
    },
    {
      "id": "pod/default/cache-service",
      "distance": 2
    }
  ],
  "impact_count": 2,
  "max_depth": 2,
  "risk_level": "MEDIUM",
  "timestamp": "2026-02-05T10:00:00Z"
}
```

---

### Get Dependencies
```http
GET /dependencies/{asset_id}?depth=5
```

**Example**:
```
GET /dependencies/pod/default/app-service-1
```

**Response**: `200 OK`
```json
{
  "asset_id": "pod/default/app-service-1",
  "dependencies": [
    {
      "id": "service/default/db-service",
      "type": "service",
      "distance": 1
    },
    {
      "id": "pod/default/database-1",
      "type": "pod",
      "distance": 2
    }
  ],
  "dependency_count": 2,
  "timestamp": "2026-02-05T10:00:00Z"
}
```

---

### Find Dependency Path
```http
GET /path/{source_id}/{target_id}
```

**Example**:
```
GET /path/pod/default/app-service/pod/default/database-1
```

**Response**: `200 OK`
```json
{
  "connected": true,
  "source": "pod/default/app-service",
  "target": "pod/default/database-1",
  "path": [
    "pod/default/app-service",
    "service/default/db-service",
    "pod/default/database-1"
  ],
  "hops": 2,
  "timestamp": "2026-02-05T10:00:00Z"
}
```

**Not Connected Response**: `200 OK`
```json
{
  "connected": false,
  "source": "pod/default/app-service",
  "target": "pod/default/independent-service"
}
```

---

### Assess Change Impact
```http
POST /change-impact?asset_id=...&change_type=update
```

**Query Parameters**:
- `asset_id`: Asset being changed
- `change_type` (optional): Type of change (update, delete, config, etc.)

**Example**:
```
POST /change-impact?asset_id=pod/default/database-1&change_type=update
```

**Response**: `200 OK`
```json
{
  "asset_id": "pod/default/database-1",
  "change_type": "update",
  "affected_count": 3,
  "affected_assets": [
    {
      "id": "pod/default/app-service-1",
      "type": "pod"
    },
    {
      "id": "pod/default/app-service-2",
      "type": "pod"
    },
    {
      "id": "deployment/default/cache",
      "type": "deployment"
    }
  ],
  "risk_score": 5,
  "recommendation": "MEDIUM RISK - Several dependent assets",
  "timestamp": "2026-02-05T10:00:00Z"
}
```

---

### Get Graph Topology
```http
GET /graph/topology
```

**Response**: `200 OK`
```json
{
  "nodes": [
    {
      "id": "pod/default/nginx-123",
      "type": "pod",
      "name": "nginx-123"
    },
    {
      "id": "node/worker-1",
      "type": "node",
      "name": "worker-1"
    }
  ],
  "edges": [
    {
      "source": "pod/default/nginx-123",
      "target": "node/worker-1",
      "type": "RUNS_ON"
    }
  ],
  "timestamp": "2026-02-05T10:00:00Z"
}
```

---

## Error Responses

All endpoints use standard HTTP status codes and error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
  "detail": "Asset not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error message"
}
```

---

## Rate Limiting

- **Graph Service**: 1000 requests/minute per client
- **Impact Engine**: 500 requests/minute per client

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1675000060
```

---

## Event Schema

### Event Envelope
```json
{
  "event_type": "ASSET_DISCOVERED",
  "source": "k8s-controller",
  "timestamp": "2026-02-05T10:00:00Z",
  "payload": {
    "id": "pod/default/nginx-123",
    "type": "pod",
    "name": "nginx-123",
    "namespace": "default",
    "properties": {}
  }
}
```

### Event Types
- `ASSET_DISCOVERED`: New asset found
- `ASSET_DELETED`: Asset removed
- `ASSET_UPDATED`: Asset configuration changed
- `CONFIG_DRIFT`: Configuration mismatch detected
- `DEPENDENCY_CHANGED`: Relationship changed
- `IMPACT_ANALYSIS`: Impact analysis complete

---

## Examples

### Create a Pod Asset
```bash
curl -X POST http://localhost:8000/asset \
  -H "Content-Type: application/json" \
  -d '{
    "id": "pod/default/my-app",
    "type": "pod",
    "name": "my-app",
    "properties": {
      "image": "my-app:latest",
      "replicas": 3
    }
  }'
```

### Get Impact Analysis
```bash
curl http://localhost:8001/impact/pod/default/my-app
```

### Find Dependency Path
```bash
curl http://localhost:8001/path/pod/default/app/pod/default/database
```

### List All Assets
```bash
curl http://localhost:8000/assets?limit=50
```

---

## Pagination

Supported on list endpoints:
```http
GET /assets?limit=50&offset=100
```

Response includes:
```json
{
  "assets": [...],
  "count": 50,
  "total": 1000,
  "offset": 100,
  "limit": 50
}
```

---

## Versioning

- Current API version: `v1`
- Future versions will be available at `/api/v2/`

---

## SDK/Client Libraries

Future implementations:
- Python SDK
- Go SDK
- JavaScript SDK
- TypeScript SDK

---

## Support

For API issues:
- GitHub Issues: [repository]/issues
- Email: support@cmdb.example.com
- Slack: #cmdb-support
