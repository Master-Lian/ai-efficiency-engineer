#!/bin/bash

set -e

echo "=== 5G NR Agents System K8s 部署脚本 ==="

IMAGE_NAME="5g-nr-agent-system"
IMAGE_TAG="latest"
NAMESPACE="5g-nr-agents"

echo "[1/6] 构建 Docker 镜像..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo "[2/6] 加载镜像到 K8s..."
if command -v minikube &> /dev/null; then
    minikube image load ${IMAGE_NAME}:${IMAGE_TAG}
elif command -v kind &> /dev/null; then
    kind load docker-image ${IMAGE_NAME}:${IMAGE_TAG}
fi

echo "[3/6] 创建命名空间..."
kubectl apply -f k8s/namespace.yaml

echo "[4/6] 应用配置..."
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/pvc.yaml

echo "[5/6] 部署应用..."
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml

echo "[6/6] 配置 Ingress（可选）..."
echo "如需启用 Ingress，请取消注释 k8s/ingress.yaml 并执行:"
echo "  kubectl apply -f k8s/ingress.yaml"

echo ""
echo "=== 部署完成 ==="
echo "查看部署状态: kubectl get pods -n ${NAMESPACE}"
echo "查看服务状态: kubectl get svc -n ${NAMESPACE}"
echo "查看日志: kubectl logs -f -n ${NAMESPACE} -l app=5g-nr-agent"
