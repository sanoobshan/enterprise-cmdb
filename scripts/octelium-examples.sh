#!/bin/bash

# Enterprise CMDB with Octelium - Testing & Examples
# Demonstrates WHO, WHAT, WHEN, WHY audit logging

set -e

BASE_URL="http://localhost:8000"
AUDIT_URL="http://localhost:8002"

echo "================================================"
echo "Enterprise CMDB - Octelium Integration Examples"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Example 1: Create an asset with incident response reason
echo -e "${BLUE}Example 1: Asset creation during incident response${NC}"
echo "Creating pod with incident response reason..."

INCIDENT_ID="INC-20260205-001"
USER="alice@company.com"

curl -X POST ${BASE_URL}/asset \
  -H "Content-Type: application/json" \
  -H "X-User-ID: ${USER}" \
  -H "X-User-Email: ${USER}" \
  -H "X-Access-Reason: incident-response-${INCIDENT_ID}" \
  -d '{
    "id": "pod/production/critical-app",
    "type": "pod",
    "name": "critical-app",
    "properties": {
      "namespace": "production",
      "critical": true
    }
  }'

echo ""
echo -e "${GREEN}✓ Asset created with audit trail${NC}"
echo ""

# Example 2: Update asset for maintenance
echo -e "${BLUE}Example 2: Asset update during scheduled maintenance${NC}"
echo "Updating database pod for maintenance..."

MAINTENANCE_WINDOW="maintenance-2026-02-06"
USER="ops@company.com"

curl -X POST ${BASE_URL}/asset \
  -H "Content-Type: application/json" \
  -H "X-User-ID: ${USER}" \
  -H "X-User-Email: ${USER}" \
  -H "X-Access-Reason: ${MAINTENANCE_WINDOW}" \
  -d '{
    "id": "pod/production/database",
    "type": "pod",
    "name": "database",
    "properties": {
      "namespace": "production",
      "status": "under-maintenance"
    }
  }'

echo ""
echo -e "${GREEN}✓ Asset updated with maintenance reason${NC}"
echo ""

# Example 3: Query audit logs by user
echo -e "${BLUE}Example 3: Query audit logs for a user${NC}"
echo "Getting all actions by alice@company.com..."

curl -s ${AUDIT_URL}/audit/user/alice@company.com | jq .

echo ""
echo -e "${GREEN}✓ User audit history retrieved${NC}"
echo ""

# Example 4: Query audit logs by resource
echo -e "${BLUE}Example 4: Query audit logs for a specific resource${NC}"
echo "Getting all changes to critical-app pod..."

curl -s ${AUDIT_URL}/audit/resource/asset/pod/production/critical-app | jq .

echo ""
echo -e "${GREEN}✓ Resource audit history retrieved${NC}"
echo ""

# Example 5: Query logs by action
echo -e "${BLUE}Example 5: Query audit logs by action type${NC}"
echo "Finding all create operations..."

curl -s ${AUDIT_URL}/audit/action/create | jq .

echo ""
echo -e "${GREEN}✓ Action audit logs retrieved${NC}"
echo ""

# Example 6: Query logs by access reason
echo -e "${BLUE}Example 6: Query logs by access reason (WHY)${NC}"
echo "Finding all incident response actions..."

curl -s ${AUDIT_URL}/audit/reason/incident-response | jq .

echo ""
echo -e "${GREEN}✓ Access reason audit logs retrieved${NC}"
echo ""

# Example 7: Get complete timeline with WHO, WHAT, WHEN, WHY
echo -e "${BLUE}Example 7: Complete audit timeline (WHO, WHAT, WHEN, WHY)${NC}"
echo "Getting timeline for critical-app pod..."

curl -s ${AUDIT_URL}/audit/timeline/asset/pod/production/critical-app | jq .

echo ""
echo -e "${GREEN}✓ Complete audit timeline retrieved${NC}"
echo ""

# Example 8: Generate compliance report
echo -e "${BLUE}Example 8: Compliance report generation${NC}"
echo "Generating compliance report for date range..."

curl -s "${AUDIT_URL}/audit/compliance-report?start_date=2026-02-01&end_date=2026-02-10" | jq .

echo ""
echo -e "${GREEN}✓ Compliance report generated${NC}"
echo ""

# Example 9: Troubleshooting scenario
echo -e "${BLUE}Example 9: Incident investigation - find all related access${NC}"
echo "Investigating incident INC-20260205-001..."

echo "Step 1: Find all accesses related to this incident"
curl -s ${AUDIT_URL}/audit/reason/incident-response-INC-20260205-001 | jq '.logs[] | {timestamp, user_id, action, resource_id, status}'

echo ""
echo "Step 2: Get complete timeline of affected resource"
curl -s ${AUDIT_URL}/audit/timeline/asset/pod/production/critical-app | jq '.timeline[] | {timestamp, who: .who.user_id, what: .what.action, why: .why}'

echo ""
echo -e "${GREEN}✓ Incident investigation complete${NC}"
echo ""

# Example 10: Access pattern analysis
echo -e "${BLUE}Example 10: Analyze access patterns${NC}"
echo "Finding who accessed production resources..."

curl -s "${AUDIT_URL}/audit/compliance-report" | jq '.by_user'

echo ""
echo -e "${GREEN}✓ Access pattern analysis complete${NC}"
echo ""

# Summary
echo ""
echo "================================================"
echo "Summary: Octelium Audit Trail Capabilities"
echo "================================================"
echo ""
echo -e "${BLUE}WHO:${NC}  User identity from X-User-ID header"
echo "      Example: alice@company.com"
echo ""
echo -e "${BLUE}WHAT:${NC} Operation/action performed"
echo "      Examples: create, read, update, delete"
echo ""
echo -e "${BLUE}WHEN:${NC} Timestamp of operation (automatic)"
echo "      Example: 2026-02-05T10:30:00Z"
echo ""
echo -e "${BLUE}WHY:${NC}  Access reason from X-Access-Reason header"
echo "      Examples:"
echo "        - incident-response-INC-123"
echo "        - maintenance-2026-02-06"
echo "        - troubleshooting-connection-issue"
echo "        - investigation-security-audit"
echo ""
echo "================================================"
echo "Query Methods"
echo "================================================"
echo ""
echo "1. By User:        /audit/user/{user_id}"
echo "2. By Resource:    /audit/resource/{type}/{id}"
echo "3. By Action:      /audit/action/{action}"
echo "4. By Reason:      /audit/reason/{reason}"
echo "5. Timeline:       /audit/timeline/{type}/{id}"
echo "6. Compliance:     /audit/compliance-report"
echo ""
echo -e "${GREEN}All examples completed successfully!${NC}"
echo ""
