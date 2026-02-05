-- Migration script for audit logging database
-- Run this to initialize the audit_logs table

BEGIN;

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    user_id VARCHAR(255) NOT NULL,
    user_email VARCHAR(255),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    reason TEXT,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    octelium_session_id VARCHAR(255)
);

-- Create indexes for efficient querying
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_status ON audit_logs(status);
CREATE INDEX idx_audit_logs_reason ON audit_logs USING GIN(to_tsvector('english', reason));

-- Create view for compliance reporting
CREATE OR REPLACE VIEW audit_summary AS
SELECT 
    DATE(timestamp) as date,
    action,
    COUNT(*) as count,
    COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
    COUNT(CASE WHEN status = 'failure' THEN 1 END) as failure_count
FROM audit_logs
GROUP BY DATE(timestamp), action
ORDER BY date DESC, action;

-- Create view for user activity
CREATE OR REPLACE VIEW user_activity AS
SELECT 
    user_id,
    user_email,
    COUNT(*) as total_actions,
    COUNT(DISTINCT DATE(timestamp)) as active_days,
    MAX(timestamp) as last_action,
    array_agg(DISTINCT action) as actions_performed
FROM audit_logs
GROUP BY user_id, user_email
ORDER BY total_actions DESC;

-- Create view for resource audit trail
CREATE OR REPLACE VIEW resource_audit_trail AS
SELECT 
    resource_type,
    resource_id,
    COUNT(*) as total_changes,
    array_agg(DISTINCT action) as change_types,
    array_agg(DISTINCT user_id) as modified_by,
    MIN(timestamp) as first_change,
    MAX(timestamp) as last_change
FROM audit_logs
GROUP BY resource_type, resource_id
ORDER BY last_change DESC;

-- Create view for access by reason
CREATE OR REPLACE VIEW access_by_reason AS
SELECT 
    reason,
    COUNT(*) as count,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(DISTINCT DATE(timestamp)) as active_days,
    array_agg(DISTINCT action) as actions
FROM audit_logs
WHERE reason IS NOT NULL
GROUP BY reason
ORDER BY count DESC;

-- Create stored procedure for audit cleanup (retention policy)
CREATE OR REPLACE FUNCTION cleanup_old_audits(days_to_retain INTEGER DEFAULT 90)
RETURNS TABLE(deleted_count INTEGER) AS $$
DECLARE
    deleted_rows INTEGER;
BEGIN
    DELETE FROM audit_logs 
    WHERE timestamp < NOW() - INTERVAL '1 day' * days_to_retain;
    GET DIAGNOSTICS deleted_rows = ROW_COUNT;
    
    RETURN QUERY SELECT deleted_rows;
END;
$$ LANGUAGE plpgsql;

-- Create stored procedure for compliance report
CREATE OR REPLACE FUNCTION generate_compliance_report(
    start_date TIMESTAMP DEFAULT NOW() - INTERVAL '7 days',
    end_date TIMESTAMP DEFAULT NOW()
)
RETURNS TABLE(
    report_date TIMESTAMP,
    total_events BIGINT,
    successful_events BIGINT,
    failed_events BIGINT,
    unique_users BIGINT,
    unique_resources BIGINT,
    action_breakdown JSONB
) AS $$
DECLARE
    action_breakdown JSONB;
BEGIN
    action_breakdown := (
        SELECT jsonb_object_agg(action, COUNT(*))
        FROM audit_logs
        WHERE timestamp BETWEEN start_date AND end_date
        GROUP BY action
    );
    
    RETURN QUERY
    SELECT 
        NOW(),
        COUNT(*),
        COUNT(CASE WHEN status = 'success' THEN 1 END),
        COUNT(CASE WHEN status = 'failure' THEN 1 END),
        COUNT(DISTINCT user_id),
        COUNT(DISTINCT (resource_type || '/' || resource_id)),
        action_breakdown
    FROM audit_logs
    WHERE timestamp BETWEEN start_date AND end_date;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed for your security model)
GRANT SELECT ON audit_logs TO cmdb;
GRANT INSERT ON audit_logs TO cmdb;
GRANT SELECT ON audit_summary TO cmdb;
GRANT SELECT ON user_activity TO cmdb;
GRANT SELECT ON resource_audit_trail TO cmdb;
GRANT SELECT ON access_by_reason TO cmdb;

-- Verify tables created
SELECT 
    tablename,
    (SELECT COUNT(*) FROM audit_logs) as record_count
FROM pg_tables 
WHERE tablename = 'audit_logs';

COMMIT;
