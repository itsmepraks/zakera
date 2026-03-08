#!/bin/bash
#
# Monitoring Stack Setup Script
# Install and configure Prometheus, Grafana, and Alertmanager for Zakera
#
# Usage: ./scripts/setup-monitoring.sh [options]
#
# Options:
#   --namespace NAME    Monitoring namespace (default: monitoring)
#   --skip-prometheus   Skip Prometheus installation
#   --skip-grafana      Skip Grafana installation
#   --skip-alertmanager Skip Alertmanager installation
#   --import-dashboards Import Grafana dashboards
#   --uninstall         Uninstall monitoring stack

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
NAMESPACE="monitoring"
SKIP_PROMETHEUS=false
SKIP_GRAFANA=false
SKIP_ALERTMANAGER=false
IMPORT_DASHBOARDS=false
UNINSTALL=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --namespace) NAMESPACE="$2"; shift 2 ;;
        --skip-prometheus) SKIP_PROMETHEUS=true; shift ;;
        --skip-grafana) SKIP_GRAFANA=true; shift ;;
        --skip-alertmanager) SKIP_ALERTMANAGER=true; shift ;;
        --import-dashboards) IMPORT_DASHBOARDS=true; shift ;;
        --uninstall) UNINSTALL=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

print_step() { echo -e "\n${BLUE}▶ $1${NC}"; }
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Zakera Monitoring Stack Setup           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Uninstall if requested
if [ "$UNINSTALL" = true ]; then
    print_step "Uninstalling monitoring stack..."
    
    helm uninstall prometheus -n "$NAMESPACE" 2>/dev/null || true
    helm uninstall grafana -n "$NAMESPACE" 2>/dev/null || true
    helm uninstall alertmanager -n "$NAMESPACE" 2>/dev/null || true
    
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true
    
    print_success "Monitoring stack uninstalled"
    exit 0
fi

# Check prerequisites
print_step "Checking prerequisites..."

if ! command -v helm &> /dev/null; then
    print_error "Helm not found. Please install Helm 3+"
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes"
    exit 1
fi

print_success "Prerequisites OK"

# Create namespace
print_step "Creating monitoring namespace..."

if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    kubectl create namespace "$NAMESPACE"
    kubectl label namespace "$NAMESPACE" name=monitoring
    print_success "Created namespace $NAMESPACE"
else
    print_success "Namespace $NAMESPACE exists"
fi

# Add Helm repositories
print_step "Adding Helm repositories..."

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

print_success "Helm repositories updated"

# Install Prometheus
if [ "$SKIP_PROMETHEUS" = false ]; then
    print_step "Installing Prometheus..."
    
    cat > /tmp/prometheus-values.yaml <<EOF
server:
  retention: 15d
  persistentVolume:
    enabled: true
    size: 50Gi
  resources:
    requests:
      cpu: 500m
      memory: 2Gi
    limits:
      cpu: 2000m
      memory: 8Gi
  
alertmanager:
  enabled: true
  persistence:
    enabled: true
    size: 10Gi

configmapReload:
  prometheus:
    enabled: true
  alertmanager:
    enabled: true

prometheus-node-exporter:
  enabled: true

kube-state-metrics:
  enabled: true

prometheus-pushgateway:
  enabled: false
EOF
    
    helm upgrade --install prometheus prometheus-community/prometheus \
        -n "$NAMESPACE" \
        -f /tmp/prometheus-values.yaml \
        --wait
    
    print_success "Prometheus installed"
fi

# Install Grafana
if [ "$SKIP_GRAFANA" = false ]; then
    print_step "Installing Grafana..."
    
    # Generate admin password
    GRAFANA_PASSWORD=$(openssl rand -base64 32)
    
    cat > /tmp/grafana-values.yaml <<EOF
adminPassword: ${GRAFANA_PASSWORD}

persistence:
  enabled: true
  size: 10Gi

datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
    - name: Prometheus
      type: prometheus
      url: http://prometheus-server
      access: proxy
      isDefault: true
    - name: Jaeger
      type: jaeger
      url: http://jaeger-query.monitoring:16686
      access: proxy

dashboardProviders:
  dashboardproviders.yaml:
    apiVersion: 1
    providers:
    - name: 'default'
      orgId: 1
      folder: ''
      type: file
      disableDeletion: false
      updateIntervalSeconds: 10
      options:
        path: /var/lib/grafana/dashboards/default

dashboards:
  default:
    zakera-production:
      json: |
$(cat "$PROJECT_ROOT/monitoring/grafana/dashboards/zakera-production-dashboard.json" | sed 's/^/        /')

ingress:
  enabled: true
  hosts:
    - grafana.zakera.local
  tls:
    - secretName: grafana-tls
      hosts:
        - grafana.zakera.local

resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 2Gi
EOF
    
    helm upgrade --install grafana grafana/grafana \
        -n "$NAMESPACE" \
        -f /tmp/grafana-values.yaml \
        --wait
    
    print_success "Grafana installed"
    echo -e "${GREEN}Grafana admin password:${NC} $GRAFANA_PASSWORD"
    echo -e "${YELLOW}Save this password securely!${NC}"
fi

# Configure Prometheus to scrape Zakera metrics
print_step "Configuring Prometheus scraping..."

kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-zakera-config
  namespace: $NAMESPACE
data:
  zakera-scrape.yml: |
    - job_name: 'zakera-api'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - zakera-production
          - zakera-staging
          - zakera-development
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: zakera
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: \$1:\$2
EOF

print_success "Prometheus configured for Zakera scraping"

# Import Grafana dashboards
if [ "$IMPORT_DASHBOARDS" = true ]; then
    print_step "Importing Grafana dashboards..."
    
    # Wait for Grafana to be ready
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n "$NAMESPACE" --timeout=300s
    
    # Get Grafana pod
    GRAFANA_POD=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].metadata.name}')
    
    # Import dashboards
    for dashboard in "$PROJECT_ROOT"/monitoring/grafana/dashboards/*.json; do
        if [ -f "$dashboard" ]; then
            kubectl cp "$dashboard" "$NAMESPACE/$GRAFANA_POD:/var/lib/grafana/dashboards/"
            print_success "Imported: $(basename $dashboard)"
        fi
    done
fi

# Display access information
print_step "Monitoring Stack Access Information"

echo ""
echo -e "${GREEN}Prometheus:${NC}"
kubectl port-forward -n "$NAMESPACE" svc/prometheus-server 9090:80 &
echo "  URL: http://localhost:9090"
echo "  Forward: kubectl port-forward -n $NAMESPACE svc/prometheus-server 9090:80"

echo ""
echo -e "${GREEN}Grafana:${NC}"
kubectl port-forward -n "$NAMESPACE" svc/grafana 3000:80 &
echo "  URL: http://localhost:3000"
echo "  Username: admin"
echo "  Password: $GRAFANA_PASSWORD"
echo "  Forward: kubectl port-forward -n $NAMESPACE svc/grafana 3000:80"

echo ""
echo -e "${GREEN}Alertmanager:${NC}"
kubectl port-forward -n "$NAMESPACE" svc/prometheus-alertmanager 9093:80 &
echo "  URL: http://localhost:9093"
echo "  Forward: kubectl port-forward -n $NAMESPACE svc/prometheus-alertmanager 9093:80"

echo ""
print_success "Monitoring stack setup complete! 🎉"
echo ""
echo "Run the port-forward commands above to access the dashboards."
