#!/bin/bash
NS=skala3-finalproj-class2-team8

pkill -f "kubectl port-forward.*skipa-qdrant" 2>/dev/null || true
pkill -f "kubectl port-forward.*skipa-minio"  2>/dev/null || true
sleep 1

kubectl port-forward -n $NS svc/skipa-qdrant 6333:6333  > /tmp/pf-qdrant.log 2>&1 &
kubectl port-forward -n $NS svc/skipa-minio  19000:9000 19001:9001 > /tmp/pf-minio.log  2>&1 &

echo "Port-forward started"
echo "  Qdrant:        http://localhost:6333"
echo "  MinIO API:     http://localhost:19000"
echo "  MinIO Console: http://localhost:19001"
