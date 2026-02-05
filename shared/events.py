"""
Shared event definitions and constants
"""

# Event types
ASSET_DISCOVERED = "ASSET_DISCOVERED"
ASSET_DELETED = "ASSET_DELETED"
ASSET_UPDATED = "ASSET_UPDATED"
CONFIG_DRIFT = "CONFIG_DRIFT"
DEPENDENCY_CHANGED = "DEPENDENCY_CHANGED"
IMPACT_ANALYSIS = "IMPACT_ANALYSIS"

# Asset types
ASSET_TYPE_POD = "pod"
ASSET_TYPE_DEPLOYMENT = "deployment"
ASSET_TYPE_SERVICE = "service"
ASSET_TYPE_NODE = "node"
ASSET_TYPE_DATABASE = "database"
ASSET_TYPE_VM = "vm"
ASSET_TYPE_CONTAINER = "container"

# Event envelope structure
class EventEnvelope:
    """Standard event envelope for all events"""
    def __init__(self, event_type, payload, source=None, timestamp=None):
        self.event_type = event_type
        self.payload = payload
        self.source = source
        self.timestamp = timestamp

    def to_dict(self):
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "source": self.source,
            "timestamp": self.timestamp
        }
