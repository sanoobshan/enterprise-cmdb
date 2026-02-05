# Octelium Integration - Zero Trust Access & Audit Trail

## Overview

The Enterprise CMDB Platform now integrates **Octelium**, a Zero Trust Network Access (ZTNA) platform with OpenTelemetry-native audit logging. This enables:

- **WHO** accessed what (user identity)
- **WHAT** they did (action/operation)
- **WHEN** they did it (timestamp)
- **WHY** they accessed it (reason/context)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User/Service                            │
│                   (with X-User-ID header)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
            ┌──────────▼──────────┐
            │   Octelium ZTNA     │
            │  (Access Control)   │
            │  Port: 8443 (HTTPS) │
            │  Port: 9000 (gRPC)  │
            └──────────┬──────────┘
                       │
            ┌──────────▼──────────┐
            │  Graph Service      │
            │  (Port: 8000)       │
            │                     │
            │  ┌─────────────┐    │
            │  │  Telemetry  │    │
            │  │ Middleware  │    │
            │  └─────────────┘    │
            └──────────┬──────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   ┌────▼────┐  ┌─────▼─────┐  ┌────▼──────┐
   │  Neo4j  │  │ Audit DB  │  │ Jaeger    │
   │ (Assets)│  │(PostgreSQL)   │(Tracing) │
   └─────────┘  └───────────┘  └──────────┘
        │              ▲
        │              │
        └──────────────┘
        Audit Logger Service
        (Port: 8002)
```

---

## Components

### 1. Octelium Service (Port 8443/9000)
- **Zero Trust Network Access Control**
- Validates every request
- Encrypts all traffic (WireGuard/QUIC)
- Provides identity-aware access control
- OpenTelemetry-native observability

### 2. Audit Logger Service (Port 8002)
- **Centralized Audit Trail**
- PostgreSQL database for audit logs
- REST API for querying audit history
- Tracks WHO, WHAT, WHEN, WHY for all operations
- Compliance reporting

### 3. Telemetry Middleware
- Captures all requests in Graph Service
- Sends audit events to Audit Logger
- Integrates with Jaeger for distributed tracing
- OpenTelemetry instrumentation

---

## How It Works

### Flow for CMDB Operations

```
1. User sends request with headers:
   - X-User-ID: alice@company.com
   - X-User-Email: alice@company.com
   - X-Access-Reason: troubleshooting-incident-123

2. Octelium validates:
   - Is user authenticated?
   - Does user have access to this resource?
   - Is access allowed at this time?

3. Request reaches Graph Service
   - Middleware captures request details
   - Processes the operation (create/read/update/delete)

4. Audit Logging
   - WHO: User identity from X-User-ID
   - WHAT: Operation (create asset, update relationship)
   - WHEN: Timestamp (automatic)
   - WHY: From X-Access-Reason header
   - Details: Method, path, status code, etc.

5. Tracing (OpenTelemetry)
   - Jaeger captures distributed traces
   - Shows request flow across services
   - Includes audit context

6. Audit Stored
   - PostgreSQL database
   - Indexed by user, resource, action, timestamp
   - Queryable via REST API
```

---

## Usage

### Making Requests with Audit Context

```bash
# Example: Create an asset with audit context
curl -X POST http://localhost:8000/asset \
  -H "Content-Type: application/json" \
  -H "X-User-ID: alice@company.com" \
  -H "X-User-Email: alice@company.com" \
  -H "X-Access-Reason: incident-response-for-incident-123" \
  -d '{
    "id": "pod/default/nginx-1",
    "type": "pod",
    "name": "nginx-1",
    "properties": {"namespace": "default"}
  }'
```

### Headers

Required headers for audit logging:

| Header | Description | Example |
|--------|-------------|---------|
| `X-User-ID` | User identifier | `alice@company.com` |
| `X-User-Email` | User email | `alice@company.com` |
| `X-Access-Reason` | Why accessing (for compliance) | `incident-response`, `maintenance`, `troubleshooting` |
| `X-Octelium-Session` | Octelium session ID (optional) | From Octelium auth |

### Access Reasons

Document WHY access was needed:
- `incident-response`: Responding to security/operational incident
- `troubleshooting`: Investigating operational issues
- `maintenance`: Scheduled maintenance work
- `investigation`: Security investigation
- `routine`: Routine operational tasks
- `audit`: Compliance/audit review
- `training`: Training/education purposes
- `testing`: Testing and validation

---

## Audit Logger API

### Create Audit Log
```http
POST /audit
Content-Type: application/json

{
  "user_id": "alice@company.com",
  "user_email": "alice@company.com",
  "action": "create",
  "resource_type": "asset",
  "resource_id": "pod/default/nginx-1",
  "status": "success",
  "reason": "incident-response-for-incident-123",
  "details": {
    "method": "POST",
    "path": "/asset",
    "status_code": 200
  }
}
```

### Query Audit Logs

**By User:**
```bash
GET /audit/user/alice@company.com
```

**By Resource:**
```bash
GET /audit/resource/asset/pod/default/nginx-1
```

**By Action:**
```bash
GET /audit/action/create
```

**By Access Reason:**
```bash
GET /audit/reason/incident-response
```

**Complete Timeline:**
```bash
GET /audit/timeline/asset/pod/default/nginx-1
```

Response shows complete WHO, WHAT, WHEN, WHY:
```json
{
  "resource": "asset/pod/default/nginx-1",
  "timeline": [
    {
      "timestamp": "2026-02-05T10:00:00Z",
      "who": {
        "user_id": "alice@company.com",
        "email": "alice@company.com",
        "ip": "192.168.1.100"
      },
      "what": {
        "action": "create",
        "status": "success"
      },
      "when": "2026-02-05T10:00:00Z",
      "why": "incident-response-for-incident-123",
      "details": {}
    }
  ],
  "total_changes": 1
}
```

### Compliance Report
```bash
GET /audit/compliance-report?start_date=2026-02-01&end_date=2026-02-05
```

---

## Octelium Configuration

### Zero Trust Access Rules

Example OPA policy for Octelium:

```rego
package octelium

# Allow only during business hours
deny[msg] {
    input.time.hour < 6 or input.time.hour > 22
    msg := "Access only during business hours (6 AM - 10 PM)"
}

# Require MFA for sensitive assets
deny[msg] {
    input.resource.sensitivity == "high"
    input.auth_method != "mfa"
    msg := "MFA required for sensitive assets"
}

# Enforce access from VPN
deny[msg] {
    input.resource.requires_vpn == true
    input.network.vpn_connected != true
    msg := "VPN connection required"
}

# Require approval for delete operations
deny[msg] {
    input.action == "delete"
    input.approval.status != "approved"
    msg := "Deletion requires approval"
}
```

### Deployment

```bash
# Start Octelium
docker-compose up octelium

# Verify it's running
curl -k https://localhost:8443/health

# Configure policies
octelium-cli policy apply ./octelium-policy.rego
```

---

## Tracing & Observability

### Jaeger Integration

Access Jaeger UI:
```
http://localhost:16686
```

Search for traces by:
- Service: `graph-service`
- Operation: `POST /asset`
- Tag: `user_id=alice@company.com`

### Prometheus Metrics

```bash
curl http://localhost:8000/metrics
```

Metrics tracked:
- `cmdb_asset_created_total`: Total assets created
- `cmdb_asset_deleted_total`: Total assets deleted
- `cmdb_audit_log_created_total`: Total audit logs
- `cmdb_request_duration_seconds`: Request latency

---

## Security Best Practices

### 1. Never Log Sensitive Data
```python
# DO NOT include passwords, keys, tokens
details = {
    "old_value": "***REDACTED***",
    "new_value": "***REDACTED***"
}
```

### 2. Require Reason for All Operations
- Enforce `X-Access-Reason` header
- Reject requests without valid reason
- Document organizational access reasons

### 3. Implement Approval Workflows
```bash
# For sensitive operations, require approval before execution
POST /audit/approval-required
{
  "user_id": "alice@company.com",
  "action": "delete",
  "resource_id": "asset/production/database",
  "reason": "urgent-maintenance",
  "approvers": ["bob@company.com", "carol@company.com"]
}
```

### 4. Regular Audit Reviews
```bash
# Weekly compliance reports
GET /audit/compliance-report?start_date=2026-01-29&end_date=2026-02-05
```

### 5. Alert on Suspicious Activity
- Multiple failed access attempts
- Access outside business hours
- Bulk delete operations
- Access to sensitive resources

---

## Database Schema

### audit_logs Table

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    user_id VARCHAR(255) NOT NULL,
    user_email VARCHAR(255),
    action VARCHAR(50),           -- create, read, update, delete
    resource_type VARCHAR(100),   -- asset, relationship, policy
    resource_id VARCHAR(255),
    status VARCHAR(20),            -- success, failure
    reason TEXT,                   -- WHY
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    octelium_session_id VARCHAR(255),
    INDEX (timestamp),
    INDEX (user_id),
    INDEX (resource_type, resource_id),
    INDEX (action)
);
```

---

## Compliance & Standards

### Supported Standards
- **SOC 2**: Audit trails for access and changes
- **PCI DSS**: User activity tracking
- **HIPAA**: Access logging for regulated data
- **GDPR**: Right to audit and access history
- **ISO 27001**: Access control records

### Audit Retention
- 90 days: Hot storage (PostgreSQL)
- 1 year: Archive storage (S3/GCS)
- 7 years: Compliance archive (encrypted cold storage)

---

## Integration Examples

### Incident Response
```bash
# When responding to incident INC-123, all accesses are logged
curl -X GET http://localhost:8001/impact/asset/pod/database-1 \
  -H "X-User-ID: alice@company.com" \
  -H "X-Access-Reason: incident-response-INC-123"

# Later, audit all actions for this incident
GET /audit/reason/incident-response-INC-123
```

### Maintenance Window
```bash
# Schedule maintenance with approval
curl -X POST http://localhost:8000/asset \
  -H "X-User-ID: ops@company.com" \
  -H "X-Access-Reason: maintenance-window-2026-02-10" \
  -d '{
    "id": "deployment/production/app",
    "properties": {"status": "maintenance"}
  }'

# Review all maintenance-related changes
GET /audit/reason/maintenance-window-2026-02-10
```

### Security Investigation
```bash
# Investigate who accessed a sensitive asset
GET /audit/resource/asset/secret-config

# Check timeline of all changes
GET /audit/timeline/asset/secret-config

# Find all access by a specific user in a time range
GET /audit/user/suspicious-user@company.com
```

---

## Troubleshooting

### Audit Logs Not Being Created
1. Check if Audit Logger service is running: `curl http://localhost:8002/health`
2. Verify PostgreSQL connection: Check logs
3. Check headers are being sent correctly
4. Verify network connectivity between services

### Octelium Access Denied
1. Check Octelium policy: `octelium-cli policy list`
2. Verify user identity: `X-User-ID` header
3. Check time-based access rules (business hours)
4. Check MFA requirement for resource

### Missing Traces in Jaeger
1. Verify Jaeger is running on port 6831
2. Check `JAEGER_HOST` environment variable
3. Verify services have OpenTelemetry instrumentation
4. Check network connectivity

---

## Configuration

### Environment Variables

```bash
# Audit Logger
DATABASE_URL=postgresql://cmdb:password@postgres:5432/cmdb
OCTELIUM_ENDPOINT=https://octelium:8443
AUDIT_SERVICE_URL=http://audit-logger:8002

# Graph Service
AUDIT_SERVICE_URL=http://audit-logger:8002

# Jaeger
JAEGER_HOST=localhost
JAEGER_PORT=6831

# Log Level
LOG_LEVEL=INFO
```

### Docker Compose

All services are included in `docker-compose.dev.yaml`:
```bash
docker-compose up -d
```

---

## Next Steps

1. **Deploy Octelium policies** for your organization
2. **Configure approval workflows** for sensitive operations
3. **Set up alerting** for suspicious activity
4. **Implement audit report generation** for compliance
5. **Train teams** on access reason documentation
6. **Establish audit review process** (weekly/monthly)

---

## Support & References

- **Octelium**: https://octelium.com
- **OpenTelemetry**: https://opentelemetry.io
- **Jaeger**: https://www.jaegertracing.io
- **PostgreSQL**: https://www.postgresql.org
