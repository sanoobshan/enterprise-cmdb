"""
Drift engine consumer - monitors asset changes and detects drift
"""

from kafka import KafkaConsumer
import requests
import json
import os
import logging
from typing import Dict, Any
from main import detect_drift, get_drift_details
import time

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
GRAPH_SERVICE_URL = os.getenv("GRAPH_SERVICE_URL", "http://localhost:8000")
TOPIC = "cmdb-events"

# Store of desired configurations (in production, would come from a config management system)
DESIRED_CONFIG_STORE = {}

def create_consumer():
    """Create Kafka consumer"""
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
                value_deserializer=lambda m: json.loads(m.decode()),
                group_id="cmdb-drift-engine",
                auto_offset_reset="earliest",
                enable_auto_commit=True
            )
            logger.info(f"Connected to Kafka topic '{TOPIC}'")
            return consumer
        except Exception as e:
            retry_count += 1
            logger.warning(f"Connection attempt {retry_count}/{max_retries} failed: {e}")
            if retry_count < max_retries:
                time.sleep(5)
            else:
                logger.error("Failed to connect to Kafka after all retries")
                raise

def analyze_drift(asset_id: str, actual_config: Dict[str, Any]):
    """Analyze drift for an asset"""
    
    # Get desired config from store (or API)
    desired_config = DESIRED_CONFIG_STORE.get(asset_id)
    
    if not desired_config:
        logger.debug(f"No desired config stored for {asset_id}")
        return None
    
    drift_details = get_drift_details(actual_config, desired_config)
    
    if drift_details["has_drift"]:
        logger.warning(f"Drift detected for {asset_id}")
        logger.warning(f"Drift details: {json.dumps(drift_details['differences'], indent=2)}")
        return drift_details
    else:
        logger.debug(f"No drift for {asset_id}")
        return None

def process_event(event: Dict[str, Any]):
    """Process events for drift detection"""
    try:
        event_type = event.get("event_type")
        payload = event.get("payload", {})
        asset_id = payload.get("id")
        
        logger.debug(f"Processing event: {event_type} for asset {asset_id}")
        
        if event_type == "ASSET_DISCOVERED":
            # Store initial config as actual
            actual_config = {
                "type": payload.get("type"),
                "name": payload.get("name"),
                "properties": payload.get("properties", {})
            }
            
            # Analyze drift if desired config exists
            drift = analyze_drift(asset_id, actual_config)
            
            if drift:
                # Publish drift event
                drift_event = {
                    "event_type": "CONFIG_DRIFT",
                    "source": "drift-engine",
                    "payload": {
                        "asset_id": asset_id,
                        "drift_details": drift
                    }
                }
                logger.info(f"Publishing drift event for {asset_id}")
        
        elif event_type == "ASSET_UPDATED":
            actual_config = {
                "type": payload.get("type"),
                "name": payload.get("name"),
                "properties": payload.get("properties", {})
            }
            
            drift = analyze_drift(asset_id, actual_config)
            
            if drift:
                logger.warning(f"Drift detected in updated asset: {asset_id}")
    
    except Exception as e:
        logger.error(f"Error processing event: {e}")

def main():
    """Main drift engine loop"""
    logger.info("Starting Drift Detection Engine...")
    
    consumer = create_consumer()
    
    try:
        logger.info("Listening for asset changes...")
        for message in consumer:
            event = message.value
            process_event(event)
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Consumer error: {e}")
    finally:
        consumer.close()
        logger.info("Consumer closed")

if __name__ == "__main__":
    main()
