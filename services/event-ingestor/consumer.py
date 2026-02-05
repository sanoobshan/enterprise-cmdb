"""
Kafka event consumer - processes events and sends to Graph Service
"""

from kafka import KafkaConsumer
import requests
import json
import os
import logging
from typing import Dict, Any
import time

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
GRAPH_SERVICE_URL = os.getenv("GRAPH_SERVICE_URL", "http://localhost:8000")
TOPIC = "cmdb-events"

def create_consumer():
    """Create Kafka consumer with retry logic"""
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
                value_deserializer=lambda m: json.loads(m.decode()),
                group_id="cmdb-event-ingestor",
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

def process_event(event: Dict[str, Any]):
    """Process a single event"""
    try:
        event_type = event.get("event_type")
        payload = event.get("payload", {})
        
        logger.info(f"Processing event: {event_type}")
        
        if event_type == "ASSET_DISCOVERED":
            # Create asset in graph service
            asset_data = {
                "id": payload.get("id"),
                "type": payload.get("type"),
                "name": payload.get("id"),
                "properties": {
                    "node": payload.get("node"),
                    "namespace": payload.get("namespace")
                },
                "metadata": {
                    "source": event.get("source"),
                    "discovered_at": event.get("timestamp")
                }
            }
            response = requests.post(
                f"{GRAPH_SERVICE_URL}/asset",
                json=asset_data,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Asset created: {payload.get('id')}")
        
        elif event_type == "ASSET_DELETED":
            # Delete asset from graph service
            response = requests.delete(
                f"{GRAPH_SERVICE_URL}/asset/{payload.get('id')}",
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Asset deleted: {payload.get('id')}")
        
        elif event_type == "ASSET_UPDATED":
            # Update asset in graph service
            asset_data = {
                "id": payload.get("id"),
                "type": payload.get("type"),
                "name": payload.get("name"),
                "properties": payload.get("properties", {}),
                "metadata": payload.get("metadata", {})
            }
            response = requests.post(
                f"{GRAPH_SERVICE_URL}/asset",
                json=asset_data,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Asset updated: {payload.get('id')}")
        
        else:
            logger.warning(f"Unknown event type: {event_type}")
    
    except requests.RequestException as e:
        logger.error(f"Graph Service request failed: {e}")
    except Exception as e:
        logger.error(f"Error processing event: {e}")

def main():
    """Main consumer loop"""
    logger.info("Starting Event Ingestor...")
    
    consumer = create_consumer()
    
    try:
        logger.info("Listening for events...")
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
