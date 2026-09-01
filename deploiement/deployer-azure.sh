#!/usr/bin/env bash
#
# De zéro à la plateforme en ligne sur un cluster Kubernetes Azure.
#
#   bash deploiement/deployer-azure.sh
#
# Prérequis, vérifiés au démarrage : az (connecté), terraform, ansible,
# kubectl, et une clé SSH.
#
# Six étapes, chacune reprenable : le script peut être relancé après une
# erreur sans tout recommencer, Terraform et Ansible étant idempotents.
#
#   1. machines et réseau            Terraform
#   2. cluster k3s à deux nœuds      Ansible
#   3. contrôleur d'entrée           kubectl
#   4. la plateforme                 Kustomize
#   5. rattachement à Azure          Arc
#   6. réconciliation continue       Flux
#
# NE PAS OUBLIER, les machines sont facturées à l'heure :
#
#   cd deploiement/terraform/k3s && terraform destroy -auto-approve

set -euo pipefail

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
TF="$RACINE/deploiement/terraform/k3s"
ANS="$RACINE/deploiement/ansible"
ESPACE="skillseek-azure"

GROUPE_ARC="${GROUPE_ARC:-SkillSeek-arc}"
REGION_ARC="${REGION_ARC:-westeurope}"
CLUSTER="${CLUSTER:-skillseek-azure}"
DEPOT="${DEPOT:-https://github.com/AyMB1303/skillseek-ai}"
CLE="${CLE:-$HOME/.ssh/id_ed25519.pub}"

etape() { printf '\n\033[1m━━ %s\033[0m\n' "$1"; }

# ---------------------------------------------------------------------- #
etape "Vérifications préalables"

for outil in az terraform ansible-playbook kubectl; do
  command -v "$outil" >/dev/null || { echo "« $outil » est introuvable." >&2; exit 1; }
done

az account show >/dev/null 2>&1 || { echo "Non connecté à Azure : lancez 'az login'." >&2; exit 1; }

[ -f "$CLE" ] || {
  echo "Clé publique introuvable : $CLE" >&2
  echo "Créez-en une avec : ssh-keygen -t ed25519" >&2
  exit 1; }

# L'adresse publique du poste sert à restreindre l'accès d'administration.
# Sans elle, la seule alternative serait d'ouvrir le port SSH à Internet
# entier, ce que la validation du module refuse.
MON_IP="$(curl -fsS https://api.ipify.org)/32"
echo "   accès d'administration restreint à ${MON_IP}"

ABONNEMENT="$(az account show --query id -o tsv)"
echo "   abonnement ${ABONNEMENT}"

# ---------------------------------------------------------------------- #
etape "1/6 — Machines et réseau"

terraform -chdir="$TF" init -input=false
terraform -chdir="$TF" apply -auto-approve -input=false \
  -var="abonnement=$ABONNEMENT" \
  -var="adresse_administration=$MON_IP" \
  -var="chemin_cle_publique=$CLE"

terraform -chdir="$TF" output -raw inventaire_ansible > "$ANS/inventaire.ini"
IP_CHARGE="$(terraform -chdir="$TF" output -raw ip_charge)"
echo "   nœud de charge : $IP_CHARGE"

# ---------------------------------------------------------------------- #
etape "2/6 — Cluster k3s"

(cd "$ANS" && ansible-playbook -i inventaire.ini cluster.yml)

export KUBECONFIG="$ANS/acces-cluster.yaml"
kubectl get nodes -o wide

# ---------------------------------------------------------------------- #
etape "3/6 — Contrôleur d'entrée"

# Variante « bare metal » : elle expose le contrôleur directement sur les
# ports du nœud, sans demander d'équilibreur de charge au fournisseur. C'est
# ce qui convient à un cluster auto-géré, où aucun service ne répond à une
# demande d'adresse publique.
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.3/deploy/static/provider/baremetal/deploy.yaml

kubectl -n ingress-nginx patch deployment ingress-nginx-controller --type merge -p '{
  "spec": {"template": {"spec": {
    "nodeSelector": {"role": "applicatif"},
    "hostNetwork": true,
    "dnsPolicy": "ClusterFirstWithHostNet"
  }}}}'

# Le contrôleur écoute alors sur les ports 80 et 443 du nœud lui-même, que
# le groupe de sécurité ouvre déjà. Une adresse publique de moins à gérer.
kubectl -n ingress-nginx rollout status deployment/ingress-nginx-controller --timeout=300s

# ---------------------------------------------------------------------- #
etape "4/6 — La plateforme"

kubectl apply -k "$RACINE/k8s/overlays/azure"

# L'origine autorisée n'est connue qu'ici : elle dépend de l'adresse
# attribuée à l'étape 1.
kubectl -n "$ESPACE" patch configmap skillseek-config \
  --type merge -p "{\"data\":{\"FRONTEND_ORIGIN\":\"http://${IP_CHARGE}\"}}"
kubectl -n "$ESPACE" rollout restart deployment/backend

kubectl -n "$ESPACE" rollout status statefulset/db --timeout=600s
# Le premier démarrage applique les migrations, installe les rôles et charge
# les modèles avant de répondre : la sonde de démarrage laisse dix minutes.
kubectl -n "$ESPACE" rollout status deployment/backend --timeout=1200s
kubectl -n "$ESPACE" rollout status deployment/frontend --timeout=300s

etape "Vérification depuis l'extérieur"
for _ in $(seq 1 40); do
  if curl -fsS "http://${IP_CHARGE}/api/ready" >/dev/null 2>&1; then
    echo "   le service répond"; break
  fi
  sleep 15
done

# ---------------------------------------------------------------------- #
etape "5/6 — Rattachement à Azure"

for ext in connectedk8s k8s-configuration k8s-extension; do
  az extension add --name "$ext" --upgrade --only-show-errors >/dev/null
done

for f in Microsoft.Kubernetes Microsoft.KubernetesConfiguration Microsoft.ExtendedLocation; do
  az provider register --namespace "$f" --only-show-errors >/dev/null
done
for f in Microsoft.Kubernetes Microsoft.KubernetesConfiguration Microsoft.ExtendedLocation; do
  printf '   %s ' "$f"
  for _ in $(seq 1 60); do
    etat=$(az provider show --namespace "$f" --query registrationState -o tsv)
    [ "$etat" = "Registered" ] && break
    printf '.'; sleep 10
  done
  echo " $etat"
done

az group create --name "$GROUPE_ARC" --location "$REGION_ARC" --output none
az connectedk8s connect --name "$CLUSTER" --resource-group "$GROUPE_ARC" \
  --location "$REGION_ARC" \
  --tags projet="SkillSeek AI" environnement=azure gestion=arc \
  --only-show-errors

# ---------------------------------------------------------------------- #
etape "6/6 — Réconciliation continue"

# À partir d'ici, Git est la source de vérité. Un contrôleur dans le cluster
# compare en permanence l'état réel à ce que décrit le dépôt et corrige
# l'écart. La chaîne de livraison n'a plus jamais à s'authentifier auprès du
# serveur d'API : elle pousse un commit, rien de plus.
az k8s-configuration flux create \
  --name plateforme \
  --cluster-name "$CLUSTER" --resource-group "$GROUPE_ARC" \
  --cluster-type connectedClusters \
  --scope cluster --namespace flux-system \
  --url "$DEPOT" --branch main --interval 1m \
  --kustomization name=plateforme path=./k8s/overlays/azure prune=true retry_interval=2m \
  --only-show-errors

kubectl -n flux-system get pods

# ---------------------------------------------------------------------- #
cat <<TXT

════════════════════════════════════════════════════════════
  Plateforme en ligne : http://${IP_CHARGE}

  CAPTURES POUR LE RAPPORT

  Topologie à deux nœuds, dont un marqué :
    kubectl get nodes -o wide
    kubectl describe node vm-controle | grep -A3 Taints

  Répartition des charges sur le seul nœud applicatif :
    kubectl -n ${ESPACE} get pods -o wide

  Mise à l'échelle, cloisonnement, stockage :
    kubectl -n ${ESPACE} get hpa,networkpolicy,pvc

  Réconciliation GitOps :
    kubectl -n flux-system get kustomizations,gitrepositories
    az connectedk8s show -n ${CLUSTER} -g ${GROUPE_ARC} -o table

  Auto-réparation — supprimer à la main, voir revenir :
    kubectl -n ${ESPACE} delete deployment frontend
    kubectl -n ${ESPACE} get deployment frontend -w

  Au portail : Azure Arc → Kubernetes clusters → ${CLUSTER}

  ─────────────────────────────────────────────────────────
  UNE FOIS TERMINÉ — facturation à l'heure :

    az connectedk8s delete -n ${CLUSTER} -g ${GROUPE_ARC} --yes
    az group delete --name ${GROUPE_ARC} --yes --no-wait
    cd deploiement/terraform/k3s && terraform destroy -auto-approve

  Filet si l'état Terraform est perdu :
    az group delete --name SkillSeek-cluster --yes --no-wait
════════════════════════════════════════════════════════════
TXT
