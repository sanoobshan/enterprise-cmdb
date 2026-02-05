"""
Kubernetes controller for discovering cluster resources
"""

from kubernetes import client, config, watch
import logging
import os
import time
from producer import publish
from datetime import datetime

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

def load_kubeconfig():
    """Load Kubernetes configuration"""
    try:
        # Try in-cluster config first
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config")
    except:
        try:
            # Fallback to local kubeconfig
            config.load_kube_config()
            logger.info("Loaded local kubeconfig")
        except Exception as e:
            logger.error(f"Failed to load Kubernetes config: {e}")
            raise

def discover_initial_resources():
    """Discover existing resources on startup"""
    logger.info("Discovering initial resources...")
    
    try:
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        
        # Discover Pods
        pods = v1.list_pod_for_all_namespaces()
        for pod in pods.items:
            publish_pod_discovery(pod)
        logger.info(f"Discovered {len(pods.items)} pods")
        
        # Discover Nodes
        nodes = v1.list_node()
        for node in nodes.items:
            publish_node_discovery(node)
        logger.info(f"Discovered {len(nodes.items)} nodes")
        
        # Discover Deployments
        deployments = apps_v1.list_deployment_for_all_namespaces()
        for deployment in deployments.items:
            publish_deployment_discovery(deployment)
        logger.info(f"Discovered {len(deployments.items)} deployments")
        
        # Discover Services
        services = v1.list_service_for_all_namespaces()
        for service in services.items:
            publish_service_discovery(service)
        logger.info(f"Discovered {len(services.items)} services")
    
    except Exception as e:
        logger.error(f"Error discovering initial resources: {e}")

def publish_pod_discovery(pod):
    """Publish pod discovery event"""
    event = {
        "event_type": "ASSET_DISCOVERED",
        "source": "k8s-controller",
        "timestamp": datetime.utcnow().isoformat(),
        "payload": {
            "id": f"pod/{pod.metadata.namespace}/{pod.metadata.name}",
            "type": "pod",
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "node": pod.spec.node_name,
            "labels": pod.metadata.labels or {},
            "uid": pod.metadata.uid,
            "created_at": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
        }
    }
    publish(event)
    logger.debug(f"Published pod discovery: {event['payload']['id']}")

def publish_node_discovery(node):
    """Publish node discovery event"""
    event = {
        "event_type": "ASSET_DISCOVERED",
        "source": "k8s-controller",
        "timestamp": datetime.utcnow().isoformat(),
        "payload": {
            "id": f"node/{node.metadata.name}",
            "type": "node",
            "name": node.metadata.name,
            "labels": node.metadata.labels or {},
            "uid": node.metadata.uid,
            "created_at": node.metadata.creation_timestamp.isoformat() if node.metadata.creation_timestamp else None
        }
    }
    publish(event)
    logger.debug(f"Published node discovery: {event['payload']['id']}")

def publish_deployment_discovery(deployment):
    """Publish deployment discovery event"""
    event = {
        "event_type": "ASSET_DISCOVERED",
        "source": "k8s-controller",
        "timestamp": datetime.utcnow().isoformat(),
        "payload": {
            "id": f"deployment/{deployment.metadata.namespace}/{deployment.metadata.name}",
            "type": "deployment",
            "name": deployment.metadata.name,
            "namespace": deployment.metadata.namespace,
            "labels": deployment.metadata.labels or {},
            "uid": deployment.metadata.uid,
            "replicas": deployment.spec.replicas,
            "created_at": deployment.metadata.creation_timestamp.isoformat() if deployment.metadata.creation_timestamp else None
        }
    }
    publish(event)
    logger.debug(f"Published deployment discovery: {event['payload']['id']}")

def publish_service_discovery(service):
    """Publish service discovery event"""
    event = {
        "event_type": "ASSET_DISCOVERED",
        "source": "k8s-controller",
        "timestamp": datetime.utcnow().isoformat(),
        "payload": {
            "id": f"service/{service.metadata.namespace}/{service.metadata.name}",
            "type": "service",
            "name": service.metadata.name,
            "namespace": service.metadata.namespace,
            "labels": service.metadata.labels or {},
            "uid": service.metadata.uid,
            "cluster_ip": service.spec.cluster_ip,
            "created_at": service.metadata.creation_timestamp.isoformat() if service.metadata.creation_timestamp else None
        }
    }
    publish(event)
    logger.debug(f"Published service discovery: {event['payload']['id']}")

def watch_pods():
    """Watch for pod changes"""
    logger.info("Starting pod watcher...")
    
    load_kubeconfig()
    v1 = client.CoreV1Api()
    w = watch.Watch()
    
    try:
        for event in w.stream(v1.list_pod_for_all_namespaces, timeout_seconds=None):
            pod = event["object"]
            event_type = event["type"]
            
            if event_type == "ADDED":
                publish_pod_discovery(pod)
            elif event_type == "DELETED":
                publish({
                    "event_type": "ASSET_DELETED",
                    "source": "k8s-controller",
                    "timestamp": datetime.utcnow().isoformat(),
                    "payload": {
                        "id": f"pod/{pod.metadata.namespace}/{pod.metadata.name}",
                        "type": "pod"
                    }
                })
            elif event_type == "MODIFIED":
                publish({
                    "event_type": "ASSET_UPDATED",
                    "source": "k8s-controller",
                    "timestamp": datetime.utcnow().isoformat(),
                    "payload": {
                        "id": f"pod/{pod.metadata.namespace}/{pod.metadata.name}",
                        "type": "pod",
                        "name": pod.metadata.name,
                        "namespace": pod.metadata.namespace
                    }
                })
    
    except Exception as e:
        logger.error(f"Error watching pods: {e}")

def watch_nodes():
    """Watch for node changes"""
    logger.info("Starting node watcher...")
    
    load_kubeconfig()
    v1 = client.CoreV1Api()
    w = watch.Watch()
    
    try:
        for event in w.stream(v1.list_node, timeout_seconds=None):
            node = event["object"]
            event_type = event["type"]
            
            if event_type == "ADDED":
                publish_node_discovery(node)
            elif event_type == "DELETED":
                publish({
                    "event_type": "ASSET_DELETED",
                    "source": "k8s-controller",
                    "timestamp": datetime.utcnow().isoformat(),
                    "payload": {
                        "id": f"node/{node.metadata.name}",
                        "type": "node"
                    }
                })
    
    except Exception as e:
        logger.error(f"Error watching nodes: {e}")

def main():
    """Main controller loop"""
    logger.info("Starting Kubernetes Controller...")
    
    try:
        load_kubeconfig()
        
        # Discover initial resources
        discover_initial_resources()
        
        # Start watching for changes
        logger.info("Starting watchers...")
        
        # Note: In production, run these with threading or asyncio
        # For now, we'll just watch pods
        watch_pods()
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Controller error: {e}")
        time.sleep(5)
        main()

if __name__ == "__main__":
    main()
