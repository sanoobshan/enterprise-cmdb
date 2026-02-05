#!/bin/bash

# Enterprise CMDB Platform - Local Development Setup

set -e

echo "🚀 Setting up Enterprise CMDB Platform..."

# Check prerequisites
echo "📋 Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed."; exit 1; }

echo "✅ Prerequisites satisfied"

# Create .env if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
KAFKA_BOOTSTRAP=kafka:9092
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASS=password
POSTGRES_USER=cmdb
POSTGRES_PASSWORD=password
POSTGRES_DB=cmdb
LOG_LEVEL=INFO
EOF
    echo "✅ .env file created"
fi

# Start services
echo "🐳 Starting Docker Compose services..."
docker-compose -f docker-compose.dev.yaml up -d --build

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

# Check Neo4j
if curl -s http://localhost:7474 > /dev/null; then
    echo "✅ Neo4j is ready (http://localhost:7474)"
else
    echo "⚠️  Neo4j is not responding yet"
fi

# Check Graph Service
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Graph Service is ready (http://localhost:8000)"
else
    echo "⚠️  Graph Service is not responding yet"
fi

# Check Impact Engine
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ Impact Engine is ready (http://localhost:8001)"
else
    echo "⚠️  Impact Engine is not responding yet"
fi

echo ""
echo "=================================="
echo "🎉 Setup Complete!"
echo "=================================="
echo ""
echo "Services:"
echo "  - Neo4j:          http://localhost:7474"
echo "  - Graph Service:  http://localhost:8000"
echo "  - Impact Engine:  http://localhost:8001"
echo "  - Kafka:          localhost:9092"
echo ""
echo "Next steps:"
echo "  1. View logs:     docker-compose logs -f [service-name]"
echo "  2. Test API:      curl http://localhost:8000/health"
echo "  3. Create asset:  curl -X POST http://localhost:8000/asset -H 'Content-Type: application/json' -d '{...}'"
echo "  4. Stop services: docker-compose down"
echo ""
