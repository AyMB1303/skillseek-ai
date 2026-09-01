#!/usr/bin/env bash
#
# Met la plateforme en service sur le cluster AKS, de bout en bout.
#
#   cd deploiement/terraform/aks
#   terraform init && terraform apply
#   eval "$(terraform output -raw commande_acces)"
#   cd ../../../ && bash k8s/overlays/aks/mettre-en-service.sh
#
# À la fin, NE PAS OUBLIER :
#
#   cd deploiement/terraform/aks && terraform destroy -auto-approve
#
# Le nœud est facturé à l'heure. Un cluster oublié un week-end coûte plus
# cher que toute la démonstration.

set -euo pipefail

ESPACE="skillseek-demo"
RACINE="$(cd "$(dirname "$0")/../../.." && pwd)"

etape() { printf '\n\033[1m→ %s\033[0m\n' "$1"; }

etape "Contrôleur d'entrée"
# Installé depuis le manifeste officiel plutôt que par un gestionnaire de
# paquets : une dépendance de moins, et la version est lisible dans l'URL.
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.3/deploy/static/provider/cloud/deploy.yaml

echo "   attente de la disponibilité du contrôleur…"
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=300s

etape "Déploiement de la plateforme"
kubectl apply -k "$RACINE/k8s/overlays/aks"

etape "Adresse publique"
# L'équilibreur de charge Azure met une à deux minutes à attribuer une
# adresse. Interroger en boucle plutôt que dormir une durée arbitraire :
# on repart dès qu'elle est là, et on échoue franchement si elle ne vient
# jamais.
adresse=""
for _ in $(seq 1 40); do
  adresse="$(kubectl get service ingress-nginx-controller -n ingress-nginx \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)"
  [ -n "$adresse" ] && break
  sleep 15
done

if [ -z "$adresse" ]; then
  echo "Aucune adresse publique attribuée dans le délai imparti." >&2
  kubectl describe service ingress-nginx-controller -n ingress-nginx >&2
  exit 1
fi
echo "   http://${adresse}"

etape "Origine autorisée"
# Le service applicatif refuse les appels d'un navigateur dont l'origine
# n'est pas déclarée. Cette origine est l'adresse qui vient d'être
# attribuée : elle ne pouvait pas être connue avant le déploiement.
kubectl -n "$ESPACE" patch configmap skillseek-config \
  --type merge -p "{\"data\":{\"FRONTEND_ORIGIN\":\"http://${adresse}\"}}"

# Un changement de configuration ne relance pas les pods de lui-même : la
# valeur est lue au démarrage du processus.
kubectl -n "$ESPACE" rollout restart deployment/backend

etape "Attente de la mise en service"
# Le premier démarrage applique les migrations, installe les rôles et
# charge le jeu de démonstration avant de répondre. La sonde de démarrage
# décrite dans le socle laisse jusqu'à dix minutes.
kubectl -n "$ESPACE" rollout status statefulset/db --timeout=300s
kubectl -n "$ESPACE" rollout status deployment/backend --timeout=900s
kubectl -n "$ESPACE" rollout status deployment/frontend --timeout=300s

etape "Vérification depuis l'extérieur"
for _ in $(seq 1 30); do
  if curl -fsS "http://${adresse}/api/ready" >/dev/null; then
    echo "   le service répond"
    break
  fi
  sleep 10
done

etape "État du cluster"
kubectl -n "$ESPACE" get pods,svc,ingress,hpa,pvc

cat <<TXT

────────────────────────────────────────────────────────────
  Plateforme en service : http://${adresse}

  Captures utiles pour le rapport :
    kubectl -n ${ESPACE} get pods -o wide
    kubectl -n ${ESPACE} get hpa backend --watch
    kubectl -n ${ESPACE} describe pod -l app.kubernetes.io/component=service-applicatif

  Une fois terminé — le nœud est facturé à l'heure :
    cd deploiement/terraform/aks && terraform destroy -auto-approve
────────────────────────────────────────────────────────────
TXT
