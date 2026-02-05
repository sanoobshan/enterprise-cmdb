"""
Drift detection engine - detects configuration drift in assets
"""

import hashlib
import json
from typing import Dict, Any

def hash_config(config: Dict[str, Any]) -> str:
    """Generate SHA256 hash of configuration"""
    config_json = json.dumps(config, sort_keys=True)
    return hashlib.sha256(config_json.encode()).hexdigest()

def detect_drift(actual: Dict[str, Any], desired: Dict[str, Any]) -> bool:
    """
    Detect if actual configuration drifts from desired
    Returns True if drift detected
    """
    actual_hash = hash_config(actual)
    desired_hash = hash_config(desired)
    return actual_hash != desired_hash

def get_drift_details(actual: Dict[str, Any], desired: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get detailed drift information
    """
    drift_details = {
        "has_drift": detect_drift(actual, desired),
        "actual_hash": hash_config(actual),
        "desired_hash": hash_config(desired),
        "differences": {}
    }
    
    # Find specific differences
    all_keys = set(actual.keys()) | set(desired.keys())
    for key in all_keys:
        actual_val = actual.get(key)
        desired_val = desired.get(key)
        if actual_val != desired_val:
            drift_details["differences"][key] = {
                "actual": actual_val,
                "desired": desired_val
            }
    
    return drift_details
