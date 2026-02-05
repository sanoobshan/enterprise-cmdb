"""
Kafka event producer
"""

from kafka import KafkaProducer
import json
import os
import logging
from typing import Dict, Any

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
        value_serializer=lambda v: json.dumps(v).encode(),
        retries=3,
        acks="all"
    )
    logger.info(f"Connected to Kafka at {KAFKA_BOOTSTRAP}")
except Exception as e:
    logger.error(f"Failed to connect to Kafka: {e}")
    producer = None

def publish(event: Dict[str, Any], topic: str = "cmdb-events"):
    """Publish an event to Kafka"""
    if not producer:
        logger.error("Producer not initialized")
        return False
    
    try:
        future = producer.send(topic, event)
        record_metadata = future.get(timeout=10)
        logger.info(f"Event published to {record_metadata.topic} partition {record_metadata.partition}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        return False

def flush():
    """Flush all pending messages"""
    if producer:
        producer.flush()

def close():
    """Close the producer"""
    if producer:
        producer.close()
