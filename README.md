# Enterprise CMDB Platform

Event-driven, graph-based, cloud-native CMDB.

## Features
- Real-time discovery
- Graph DB (Neo4j)
- Kafka event bus
- GitOps drift detection
- Impact analysis
- Kubernetes native

## Quick Start

### Local Development
```bash
docker compose -f docker-compose.dev.yaml up --build
```

### Kubernetes
```bash
helm install cmdb ./helm/graph-service
```

## Architecture

### Services
- **graph-service**: Core asset graph database powered by Neo4j
- **event-ingestor**: Kafka consumer for event ingestion
- **drift-engine**: Detects configuration drift
- **impact-engine**: Analyzes asset dependencies and impact
- **k8s-controller**: Kubernetes-native discovery

### Infrastructure
- Neo4j: Graph database for asset relationships
- Kafka: Event streaming platform
- PostgreSQL: Optional relational data store
- Kubernetes: Container orchestration

## Development

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- kubectl (for K8s)
- Helm 3+

### Environment Variables
See `.env` for configuration.

### Testing
```bash
pytest
```

## Deployment

### Docker Compose
```bash
docker compose -f docker-compose.dev.yaml up --build
```

### Kubernetes with Helm
```bash
helm install cmdb ./helm/graph-service -n cmdb --create-namespace
```

### GitOps with ArgoCD
```bash
kubectl apply -f gitops/argocd-apps.yaml
```

## API Endpoints

- `POST /asset` - Create/update asset
- `GET /impact/{asset_id}` - Get impacted assets
- `GET /asset/{asset_id}` - Get asset details

## License

MIT
