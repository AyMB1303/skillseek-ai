#!/usr/bin/env bash
#
# Monte un cluster local et y met la plateforme en service.
#
#   bash k8s/local/demarrer.sh
#
# Prérequis : Docker en fonctionnement, `kind` et `kubectl` installés, au
# moins 8 Go alloués à Docker et 15 Go de disque libre — l'image du service
# applicatif en pèse près de quatre à elle seule.
#
# Pour tout retirer ensuite :
#
#   kind delete cluster --name skillseek

set -euo pipefail

ESPACE="skillseek-local"
RACINE="$(cd "$(dirname "$0")/../.." && pwd)"

etape() { printf '\n\033[1m→ %s\033[0m\n' "$1"; }

for outil in docker kind kubectl; do
  command -v "$outil" >/dev/null || { echo "« $outil » est introuvable." >&2; exit 1; }
done

etape "Cluster"
if kind get clusters 2>/dev/null | grep -qx skillseek; then
  echo "   déjà présent, réutilisé"
else
  kind create cluster --config "$RACINE/k8s/local/kind.yaml"
fi

etape "Contrôleur d'entrée"
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.3/deploy/static/provider/kind/deploy.yaml
echo "   attente de sa disponibilité…"
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller --timeout=300s

etape "Serveur de métriques"
# `kind` ne le fournit pas. Sans lui, la mise à l'échelle automatique reste
# à l'état « unknown » : elle est bien déclarée, mais aucune mesure ne lui
# parvient. L'option qui suit désactive la vérification du certificat du
# kubelet, que ce cluster jetable signe lui-même.
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deployment metrics-server -n kube-system --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl rollout status deployment/metrics-server -n kube-system --timeout=180s

etape "Tirage des images"
# Fait explicitement, puis chargé dans le cluster : sans cela chaque pod
# tire pour son compte, et les quatre gigaoctets descendent plusieurs fois.
docker pull ghcr.io/aymb1303/skillseek-ai/backend:latest
docker pull ghcr.io/aymb1303/skillseek-ai/frontend:latest
kind load docker-image --name skillseek \
  ghcr.io/aymb1303/skillseek-ai/backend:latest \
  ghcr.io/aymb1303/skillseek-ai/frontend:latest

etape "Déploiement"
kubectl apply -k "$RACINE/k8s/overlays/local"

etape "Attente de la mise en service"
kubectl -n "$ESPACE" rollout status statefulset/db --timeout=300s
# La sonde de démarrage laisse jusqu'à dix minutes : le service applique les
# migrations, installe les rôles et charge ses modèles avant de répondre.
kubectl -n "$ESPACE" rollout status deployment/backend --timeout=900s
kubectl -n "$ESPACE" rollout status deployment/frontend --timeout=300s

etape "Vérification depuis l'extérieur"
for _ in $(seq 1 30); do
  if curl -fsS http://localhost:8080/api/ready >/dev/null 2>&1; then
    echo "   le service répond"
    break
  fi
  sleep 10
done

etape "État du cluster"
kubectl -n "$ESPACE" get pods,svc,ingress,hpa,pvc

cat <<TXT

────────────────────────────────────────────────────────────
  Plateforme en service : http://localhost:8080

  Captures pour le rapport :
    kubectl -n ${ESPACE} get pods -o wide
    kubectl -n ${ESPACE} get hpa backend
    kubectl -n ${ESPACE} describe pod -l app.kubernetes.io/component=service-applicatif
    kubectl -n ${ESPACE} get networkpolicy

  Retirer le cluster :
    kind delete cluster --name skillseek
────────────────────────────────────────────────────────────
TXT
