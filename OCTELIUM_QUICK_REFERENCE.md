# Octelium Integration - Quick Reference Guide

## WHO, WHAT, WHEN, WHY Framework

### WHO - User Identity
```
X-User-ID: alice@company.com
X-User-Email: alice@company.com
```
- Identifies the person or service accessing the system
- Required for all audit logs
- Can be used to track user's access history

### WHAT - Operation/Action
```
create   - Creating new asset or relationship
read     - Accessing/querying asset details
update   - Modifying asset or relationship
delete   - Removing asset or relationship
access   - User logged in or accessed system
```
- Automatically captured by the system
- Indexed in database for quick queries
- Can filter logs by action type

### WHEN - Timestamp
```
2026-02-05T10:30:45.123456Z
```
- Automatically recorded
- UTC timezone
- Can query logs by date range
- Used for timeline analysis

### WHY - Access Reason
```
X-Access-Reason: incident-response-INC-123
X-Access-Reason: maintenance-2026-02-06
X-Access-Reason: troubleshooting-db-slow-query
X-Access-Reason: investigation-security-audit
```
- Documented by the accessor
- Required for compliance
- Enables context-aware access control
- Supports investigations and audits

---

## How to Use - Common Scenarios

### Scenario 1: Incident Response
```bash
# During incident response, all accesses are logged with context
curl -X GET http://localhost:8001/impact/asset/database-1 \
  -H "X-User-ID: alice@company.com" \
  -H "X-Access-Reason: incident-response-INC-20260205-001"

# Later, query all accesses related to this incident
GET /audit/reason/incident-response-INC-20260205-001
```

### Scenario 2: Maintenance Window
```bash
# Perform maintenance with scheduled reason
curl -X POST http://localhost:8000/asset \
  -H "X-User-ID: ops@company.com" \
  -H "X-Access-Reason: maintenance-2026-02-10-postgres-upgrade"

# Review all maintenance-related changes
GET /audit/reason/maintenance-2026-02-10-postgres-upgrade
```

### Scenario 3: Investigating Suspicious Activity
```bash
# Check user's access history
GET /audit/user/suspicious-user@company.com

# Check specific resource's change history
GET /audit/timeline/asset/critical-database

# Find access during unusual hours
GET /audit/action/access?timestamp=2026-02-05T23:30:00Z
```

### Scenario 4: Compliance Audit
```bash
# Get compliance report for date range
GET /audit/compliance-report?start_date=2026-01-01&end_date=2026-02-05

# Review who accessed PII
GET /audit/reason/data-access-review

# Generate statistics by user
GET /audit/compliance-report (see by_user field)
```

---

## API Quick Reference

### Query Endpoints

| Endpoint | Purpose | Example |
|----------|---------|---------|
| `GET /audit/user/{id}` | User's action history | `/audit/user/alice@company.com` |
| `GET /audit/resource/{type}/{id}` | Resource change history | `/audit/resource/asset/pod/nginx` |
| `GET /audit/action/{action}` | All actions of type | `/audit/action/delete` |
| `GET /audit/reason/{reason}` | Access by reason (WHY) | `/audit/reason/incident-response` |
| `GET /audit/timeline/{type}/{id}` | Complete WHO/WHAT/WHEN/WHY | `/audit/timeline/asset/database` |
| `GET /audit/compliance-report` | Compliance statistics | `?start_date=...&end_date=...` |

### Creating Records

```bash
POST /audit
Content-Type: application/json

{
  "user_id": "alice@company.com",
  "user_email": "alice@company.com",
  "action": "create",
  "resource_type": "asset",
  "resource_id": "pod/default/nginx",
  "status": "success",
  "reason": "incident-response-INC-123",
  "details": { ... }
}
```

---

## Database Views (SQL)

### View Audit Summary
```sql
SELECT * FROM audit_summary WHERE date = CURRENT_DATE;
```

### View User Activity
```sql
SELECT * FROM user_activity ORDER BY total_actions DESC;
```

### View Resource Audit Trail
```sql
SELECT * FROM resource_audit_trail 
WHERE resource_id = 'pod/default/nginx';
```

### View Access by Reason
```sql
SELECT * FROM access_by_reason ORDER BY count DESC;
```

### Generate Compliance Report
```sql
SELECT * FROM generate_compliance_report(
  '2026-01-01'::TIMESTAMP,
  '2026-02-05'::TIMESTAMP
);
```

---

## Best Practices

### 1. Always Provide Access Reason
```bash
# ❌ Bad - no reason
-H "X-User-ID: alice@company.com"

# ✅ Good - clear reason
-H "X-Access-Reason: incident-response-INC-123"
```

### 2. Use Consistent Reason Formats
```
incident-response-{TICKET_ID}
maintenance-{DATE}-{DESCRIPTION}
troubleshooting-{ISSUE}
investigation-{TYPE}
routine-{TASK}
audit-{AUDIT_ID}
training-{COURSE}
testing-{TEST}
```

### 3. Document Sensitive Operations
```bash
# For critical operations, include detailed reason
-H "X-Access-Reason: incident-response-INC-123-database-corruption"
```

### 4. Review Logs Regularly
```bash
# Daily compliance review
GET /audit/compliance-report?start_date=2026-02-04&end_date=2026-02-05

# Weekly user activity
GET /audit/compliance-report?start_date=2026-01-29&end_date=2026-02-05
```

### 5. Archive Old Logs
```sql
-- Cleanup logs older than 90 days
SELECT cleanup_old_audits(90);
```

---

## Octelium Zero Trust Policies

### Time-Based Access
```rego
# Allow only during business hours
deny[msg] if {
    hour < 6 or hour > 22
    msg := "Access outside business hours"
}
```

### MFA Requirements
```rego
# Require MFA for critical operations
deny[msg] if {
    action == "delete"
    auth.mfa != true
    msg := "MFA required for delete operations"
}
```

### IP Whitelisting
```rego
# Restrict access to VPN
deny[msg] if {
    resource.requires_vpn == true
    network.vpn_connected != true
    msg := "VPN required to access this resource"
}
```

### Approval Workflows
```rego
# Require approval for critical changes
deny[msg] if {
    action == "delete_asset"
    approval.status != "approved"
    msg := "Deletion requires approval"
}
```

---

## Monitoring & Alerts

### Key Metrics to Track
- Failed access attempts (status = "failure")
- Bulk operations (count > threshold)
- Unusual access times (outside business hours)
- Critical resource access
- User access pattern changes

### Alert Examples
```sql
-- Alert on failed operations
SELECT * FROM audit_logs 
WHERE status = 'failure' 
AND timestamp > NOW() - INTERVAL '1 hour';

-- Alert on bulk deletes
SELECT * FROM audit_logs 
WHERE action = 'delete' 
AND reason NOT LIKE 'maintenance%';

-- Alert on unusual users
SELECT user_id, COUNT(*) 
FROM audit_logs 
WHERE DATE(timestamp) = CURRENT_DATE
GROUP BY user_id 
HAVING COUNT(*) > 100;
```

---

## Integration Points

### With Incident Management
```
Incident → Create with X-Access-Reason: incident-response-INC-123
         → Query audit logs: GET /audit/reason/incident-response-INC-123
         → Get timeline: GET /audit/timeline/asset/{resource}
         → Generate report
```

### With Change Management
```
Change Request → Create with X-Access-Reason: maintenance-CHG-456
              → Document changes in audit logs
              → Verify changes via timeline
              → Close with audit trail
```

### With Compliance Audits
```
Audit Period → Generate report: GET /audit/compliance-report
             → Review user activity: GET /audit/compliance-report
             → Export audit logs
             → Document findings
```

---

## Troubleshooting

### Audit Logs Not Appearing
1. Check Audit Logger service: `curl http://localhost:8002/health`
2. Check PostgreSQL connection
3. Verify headers: X-User-ID, X-Access-Reason
4. Check service logs: `docker-compose logs audit-logger`

### Query Returns No Results
1. Verify resource_id format matches database
2. Check timestamp format: `YYYY-MM-DDTHH:MM:SSZ`
3. Check user_id spelling and case
4. Use compliance report to find available data

### Performance Issues
1. Check indexes: `CREATE INDEX idx_audit_logs_...`
2. Archive old logs: `SELECT cleanup_old_audits(90)`
3. Add pagination: `?limit=50&offset=100`

---

## Example Commands

### Check Who Accessed a Resource
```bash
curl http://localhost:8002/audit/resource/asset/pod/database-1 | jq '.logs[] | {user_id, timestamp, action}'
```

### Find All Maintenance Work
```bash
curl http://localhost:8002/audit/reason/maintenance | jq '.logs[] | {user_id, timestamp, resource_id}'
```

### Get User's Activity Summary
```bash
curl http://localhost:8002/audit/user/alice@company.com | jq '{user: .user_id, actions: [.logs[].action] | group_by(.) | map({action: .[0], count: length})}'
```

### Timeline for Incident Investigation
```bash
curl http://localhost:8002/audit/timeline/asset/critical-service | jq '.timeline[] | {when: .timestamp, who: .who.user_id, what: .what.action, why: .why}'
```

---

## Additional Resources

- **Octelium**: https://octelium.com
- **OpenTelemetry**: https://opentelemetry.io
- **PostgreSQL Docs**: https://www.postgresql.org/docs
- **Audit Logging Best Practices**: https://www.auditboard.com
- **Compliance Frameworks**: https://www.auditboard.com/blog/

---

## Support

For issues or questions:
1. Check logs: `docker-compose logs audit-logger`
2. Test connectivity: `curl http://localhost:8002/health`
3. Review documentation: `docs/OCTELIUM_INTEGRATION.md`
4. Run examples: `bash scripts/octelium-examples.sh`
