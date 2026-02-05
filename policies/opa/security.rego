package cmdb

# Deny public databases
deny[msg] {
    input.type == "database"
    input.public == true
    msg := "Public database not allowed - security violation"
}

# Deny non-encrypted storage
deny[msg] {
    input.type == "storage"
    input.encrypted == false
    msg := "Storage must be encrypted"
}

# Warn about missing backup
warn[msg] {
    input.type == "database"
    input.backup_enabled == false
    msg := "Database backup not enabled"
}

# Enforce resource limits
deny[msg] {
    input.type == "container"
    input.memory_limit == null
    msg := "Container must have memory limit"
}

# Compliance check for PII storage
deny[msg] {
    input.contains_pii == true
    input.encryption == false
    msg := "Assets containing PII must be encrypted"
}
