package octelium

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# ============================================================================
# Zero Trust Access Control Policies for Enterprise CMDB with Octelium
# Tracks: WHO, WHAT, WHEN, WHY
# ============================================================================

# ============================================================================
# AUTHENTICATION POLICIES
# ============================================================================

# Require strong authentication
deny[msg] if {
    input.auth.method not in ["mfa", "hardware-key", "passwordless"]
    msg := sprintf("Strong authentication required (MFA, hardware key, or passwordless). Got: %v", [input.auth.method])
}

# Require MFA for sensitive operations
deny[msg] if {
    input.action in ["delete", "update_critical"]
    input.auth.mfa != true
    msg := sprintf("MFA required for action: %s", [input.action])
}

# ============================================================================
# TIME-BASED ACCESS POLICIES
# ============================================================================

# Restrict access outside business hours for sensitive operations
deny[msg] if {
    input.resource.sensitivity == "critical"
    not office_hours
    input.approval.count == 0
    msg := "Critical resource access outside business hours requires approval"
}

office_hours if {
    hour := input.time.hour
    weekday := input.time.weekday
    hour >= 6
    hour < 22
    weekday in [1, 2, 3, 4, 5]  # Monday-Friday
}

# ============================================================================
# IDENTITY-BASED POLICIES
# ============================================================================

# Require user identity
deny[msg] if {
    not input.user.id
    msg := "User identification required"
}

# Whitelist specific users for critical operations
deny[msg] if {
    input.action == "delete_asset"
    input.resource.type == "asset"
    not input.user.id in allowed_admin_users
    msg := "Only authorized admins can delete assets"
}

allowed_admin_users := [
    "alice@company.com",
    "bob@company.com",
    "ops-team@company.com"
]

# ============================================================================
# CONTEXT-AWARE POLICIES (WHY - Access Reason)
# ============================================================================

# Require access reason for all operations
deny[msg] if {
    not input.reason
    msg := "Access reason required in X-Access-Reason header"
}

# Validate access reason format
deny[msg] if {
    input.reason
    not valid_access_reason(input.reason)
    msg := sprintf("Invalid access reason: %s. Valid reasons: incident-response, maintenance, troubleshooting, investigation, routine, audit, training, testing", [input.reason])
}

valid_access_reason(reason) if {
    parts := split(reason, "-")
    base_reason := parts[0]
    base_reason in ["incident", "maintenance", "troubleshooting", "investigation", "routine", "audit", "training", "testing"]
}

# Enhanced policies based on access reason
deny[msg] if {
    input.reason
    startswith(input.reason, "incident-response")
    # Allow broader access for incident response
    not input.incident_ticket
    msg := "Incident response requires ticket ID (e.g., incident-response-INC-123)"
}

# Approve maintenance only during maintenance windows
deny[msg] if {
    startswith(input.reason, "maintenance")
    not in_maintenance_window
    not input.approval.status == "approved"
    msg := "Maintenance outside scheduled window requires explicit approval"
}

in_maintenance_window if {
    # Define maintenance windows (e.g., weekends)
    input.time.weekday in [6, 7]  # Saturday-Sunday
}

# ============================================================================
# NETWORK-BASED POLICIES
# ============================================================================

# Require VPN for sensitive resources
deny[msg] if {
    input.resource.requires_vpn == true
    input.network.vpn_connected != true
    msg := "VPN connection required to access this resource"
}

# Restrict IP ranges for critical resources
deny[msg] if {
    input.resource.sensitivity == "critical"
    not ip_in_allowed_ranges(input.network.client_ip)
    msg := sprintf("Access from IP %s not allowed for critical resources", [input.network.client_ip])
}

ip_in_allowed_ranges(ip) if {
    # Company internal network ranges
    ip_matches(ip, "10.0.0.0/8") or
    ip_matches(ip, "172.16.0.0/12") or
    ip_matches(ip, "192.168.0.0/16")
}

# Placeholder for IP matching logic
ip_matches(ip, cidr) :- false  # Would need actual IP matching library

# ============================================================================
# RESOURCE-BASED POLICIES (WHAT)
# ============================================================================

# Prevent public database access
deny[msg] if {
    input.resource.type == "asset"
    input.resource.properties.public == true
    input.resource.properties.asset_type == "database"
    msg := "Public database access not allowed"
}

# Prevent unencrypted storage access
deny[msg] if {
    input.resource.type == "asset"
    input.resource.properties.encrypted != true
    input.action == "create"
    input.resource.properties.contains_pii == true
    msg := "PII storage must be encrypted"
}

# Restrict deletion of critical assets
deny[msg] if {
    input.action == "delete"
    input.resource.properties.critical == true
    input.approval.count < 2
    msg := sprintf("Deletion of critical resource requires 2+ approvals. Got: %d", [input.approval.count])
}

# ============================================================================
# ACTION-BASED POLICIES (WHAT)
# ============================================================================

# Audit trail for read operations on sensitive data
audit[msg] if {
    input.action in ["read", "export"]
    input.resource.sensitivity == "critical"
    msg := sprintf("Sensitive data access: %s by %s for reason: %s", [
        input.resource.id,
        input.user.id,
        input.reason
    ])
}

# Alert on bulk operations
warn[msg] if {
    input.action == "bulk_delete"
    input.count > 10
    msg := sprintf("Bulk delete operation on %d items - requires approval", [input.count])
}

# ============================================================================
# RELATIONSHIP-BASED POLICIES
# ============================================================================

# Prevent creating public dependencies
deny[msg] if {
    input.action == "create_relationship"
    input.relationship.type == "depends_on"
    input.target_asset.public == true
    input.source_asset.public != true
    msg := "Private resource cannot depend on public resource"
}

# ============================================================================
# APPROVAL-BASED POLICIES
# ============================================================================

# Require approvals for sensitive operations
deny[msg] if {
    input.action in ["delete", "update_critical", "access_secrets"]
    not approved_by_authorized_admin
    msg := "Operation requires approval from authorized admin"
}

approved_by_authorized_admin if {
    approval := input.approval
    approval.status == "approved"
    approval.approved_by in allowed_admin_users
    # Approval should be recent (within last hour)
    approval_age_seconds < 3600
}

approval_age_seconds := input.time.now - input.approval.timestamp

# ============================================================================
# COMPLIANCE POLICIES
# ============================================================================

# Ensure audit trail completeness
deny[msg] if {
    not input.timestamp
    msg := "Operation timestamp required"
}

# Enforce data retention policies
deny[msg] if {
    input.action == "delete"
    input.resource.properties.compliance_required == true
    not input.approval.includes_compliance_review
    msg := "Compliance review required before deleting regulated data"
}

# ============================================================================
# ANOMALY DETECTION
# ============================================================================

# Warn on unusual access patterns
warn[msg] if {
    input.user.previous_actions_count == 0
    msg := sprintf("New user %s - first action in system", [input.user.id])
}

# Flag bulk access
warn[msg] if {
    input.action == "list_resources"
    input.result_count > 1000
    msg := sprintf("Large result set queried: %d resources", [input.result_count])
}

# ============================================================================
# SUMMARY FUNCTIONS
# ============================================================================

# Overall decision
allow if {
    count(deny) == 0
}

# Complete audit entry with WHO, WHAT, WHEN, WHY
audit_entry[entry] if {
    entry := {
        "who": input.user.id,
        "what": input.action,
        "when": input.timestamp,
        "why": input.reason,
        "resource": input.resource.id,
        "status": "allowed"
    }
}

audit_entry[entry] if {
    entry := {
        "who": input.user.id,
        "what": input.action,
        "when": input.timestamp,
        "why": input.reason,
        "resource": input.resource.id,
        "status": "denied",
        "denial_reasons": deny
    }
}
