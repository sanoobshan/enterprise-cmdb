#!/bin/bash

# Enterprise CMDB Platform - Kubernetes Deployment

set -e

NAMESPACE="cmdb"
RELEASE_NAME="cmdb"

echo "🚀 Deploying Enterprise CMDB to Kubernetes..."

# Check prerequisites
echo "📋 Checking prerequisites..."
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required but not installed."; exit 1; }
command -v helm >/dev/null 2>&1 || { echo "Helm is required but not installed."; exit 1; }

echo "✅ Prerequisites satisfied"

# Create namespace
echo "📦 Creating namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Apply RBAC
echo "🔐 Applying RBAC..."
kubectl apply -f infra/k8s/rbac.yaml

# Apply ConfigMaps and Secrets
echo "⚙️  Applying configuration..."
kubectl apply -f infra/k8s/configmap.yaml

# Apply PVCs
echo "💾 Applying storage..."
kubectl apply -f infra/k8s/pvc.yaml

# Apply network policies
echo "🔒 Applying network policies..."
kubectl apply -f infra/k8s/network-policy.yaml

# Deploy using Helm
echo "📊 Deploying with Helm..."
helm upgrade --install $RELEASE_NAME ./helm/graph-service \
    --namespace $NAMESPACE \
    --values helm/graph-service/values.yaml

# Wait for rollout
echo "⏳ Waiting for deployment..."
kubectl rollout status deployment/graph-service -n $NAMESPACE --timeout=5m

# Apply ArgoCD apps (if ArgoCD is installed)
if kubectl get namespace argocd >/dev/null 2>&1; then
    echo "🔄 Applying ArgoCD apps..."
    kubectl apply -f gitops/argocd-apps.yaml
fi

echo ""
echo "=================================="
echo "✅ Deployment Complete!"
echo "=================================="
echo ""
echo "Check deployment status:"
echo "  kubectl get all -n $NAMESPACE"
echo ""
echo "View logs:"
echo "  kubectl logs -n $NAMESPACE -l app=graph-service -f"
echo ""
echo "Access services:"
echo "  kubectl port-forward -n $NAMESPACE svc/graph-service 8000:8000"
echo ""
