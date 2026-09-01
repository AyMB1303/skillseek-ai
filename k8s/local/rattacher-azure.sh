#!/usr/bin/env bash
#
# Rattache le cluster local à Azure, et confie son état à Git.
#
#   bash k8s/local/demarrer.sh        # le cluster doit tourner
#   bash k8s/local/rattacher-azure.sh
#
# Pourquoi ce détour plutôt qu'un cluster infogéré.
#
# L'abonnement académique n'accorde de quota qu'à des familles de machines
# que le service Kubernetes d'Azure n'accepte pas, et réciproquement :
# l'intersection est vide dans les neuf régions autorisées. Impossible donc
# de créer un cluster infogéré. Azure Arc résout la contrainte par l'autre
# bout : au lieu de louer un cluster à Azure, on rattache un cluster
# existant — d'où qu'il vienne — au plan de contrôle d'Azure.
#
# Ce n'est pas un contournement au rabais. C'est le scénario hybride, celui
# qu'on emploie pour piloter depuis Azure des clusters qui tournent dans un
# centre de données, chez un autre fournisseur, ou en bordure de réseau.
#
# Ce que le rattachement apporte concrètement :
#
#   * le cluster devient une ressource Azure — visible au portail,
#     interrogeable, soumise aux étiquettes et aux politiques ;
#   * la réconciliation GitOps par Flux : Git devient la source de vérité de
#     l'état désiré, et un contrôleur qui tourne DANS le cluster l'y ramène
#     en continu. La chaîne de livraison n'a alors plus jamais besoin de
#     s'authentifier auprès du serveur d'API : elle pousse un commit, rien
#     de plus. Les identifiants de construction n'accèdent pas au cluster,
#     et les identifiants du cluster n'en sortent pas.
#
# Coût : le rattachement est gratuit, et la configuration GitOps l'est
# jusqu'à six cœurs par abonnement. Ce cluster en compte moins.

set -euo pipefail

GROUPE="${GROUPE:-SkillSeek-arc}"
# La région porte la ressource de rattachement, pas le cluster : celui-ci
# reste sur la machine. `westeurope` est retenue parce qu'Arc y est offert,
# ce qui n'est pas le cas de toutes les régions.
REGION="${REGION:-westeurope}"
CLUSTER="${CLUSTER:-skillseek-local}"
DEPOT="${DEPOT:-https://github.com/AyMB1303/skillseek-ai}"
BRANCHE="${BRANCHE:-main}"

etape() { printf '\n\033[1m→ %s\033[0m\n' "$1"; }

command -v az >/dev/null || { echo "Azure CLI introuvable." >&2; exit 1; }
kubectl cluster-info >/dev/null 2>&1 || {
  echo "Aucun cluster joignable. Lancez d'abord k8s/local/demarrer.sh." >&2; exit 1; }

etape "Extensions de l'interface en ligne de commande"
for ext in connectedk8s k8s-configuration k8s-extension; do
  az extension add --name "$ext" --upgrade --only-show-errors >/dev/null
  echo "   $ext"
done

etape "Enregistrement des fournisseurs de ressources"
# Un abonnement neuf n'a pas ces fournisseurs actifs. L'enregistrement est
# asynchrone et prend quelques minutes ; le rattachement échouerait sans
# lui, sur un message qui n'en dit pas la cause.
for fournisseur in Microsoft.Kubernetes Microsoft.KubernetesConfiguration Microsoft.ExtendedLocation; do
  az provider register --namespace "$fournisseur" --only-show-errors >/dev/null
done
for fournisseur in Microsoft.Kubernetes Microsoft.KubernetesConfiguration Microsoft.ExtendedLocation; do
  printf '   %s ' "$fournisseur"
  for _ in $(seq 1 60); do
    etat=$(az provider show --namespace "$fournisseur" --query registrationState -o tsv)
    [ "$etat" = "Registered" ] && break
    printf '.'; sleep 10
  done
  echo " $etat"
done

etape "Groupe de ressources"
az group create --name "$GROUPE" --location "$REGION" --output none

etape "Rattachement du cluster"
# Les agents déposés dans le cluster n'ouvrent aucun port entrant : ils
# établissent une connexion sortante vers Azure et interrogent ce qu'ils
# ont à faire. C'est ce qui permet de rattacher un cluster derrière une
# machine personnelle, sans adresse publique ni règle de pare-feu.
az connectedk8s connect \
  --name "$CLUSTER" \
  --resource-group "$GROUPE" \
  --location "$REGION" \
  --tags projet="SkillSeek AI" environnement=local gestion=arc \
  --only-show-errors

etape "Réconciliation GitOps"
# `prune=true` : une ressource retirée du dépôt est retirée du cluster. Sans
# cette option, Git décrit ce qu'on ajoute mais jamais ce qu'on enlève, et
# les deux états divergent silencieusement.
#
# L'intervalle de synchronisation est court — une minute — pour que la
# démonstration soit observable ; en exploitation on l'espacerait.
az k8s-configuration flux create \
  --name plateforme \
  --cluster-name "$CLUSTER" \
  --resource-group "$GROUPE" \
  --cluster-type connectedClusters \
  --scope cluster \
  --namespace flux-system \
  --url "$DEPOT" \
  --branch "$BRANCHE" \
  --interval 1m \
  --kustomization name=plateforme path=./k8s/overlays/local prune=true retry_interval=2m \
  --only-show-errors

etape "État de la réconciliation"
az k8s-configuration flux show \
  --name plateforme --cluster-name "$CLUSTER" --resource-group "$GROUPE" \
  --cluster-type connectedClusters \
  --query "{etat:complianceState, depot:gitRepository.url, branche:gitRepository.repositoryRef.branch}" \
  -o table

kubectl -n flux-system get pods

cat <<TXT

────────────────────────────────────────────────────────────
  Cluster rattaché : ${CLUSTER}  (groupe ${GROUPE})

  Au portail Azure :
    Azure Arc → Kubernetes clusters → ${CLUSTER}
    puis l'onglet GitOps pour voir la réconciliation

  Captures utiles :
    az connectedk8s show -n ${CLUSTER} -g ${GROUPE} -o table
    kubectl -n flux-system get kustomizations,gitrepositories
    kubectl -n flux-system get pods

  Démonstration de l'auto-réparation — supprimer une ressource à la
  main et la voir revenir, puisque Git dit qu'elle doit exister :
    kubectl -n skillseek-local delete deployment frontend
    kubectl -n skillseek-local get deployment frontend -w

  Pour tout retirer :
    az k8s-configuration flux delete -n plateforme --cluster-name ${CLUSTER} \\
      -g ${GROUPE} --cluster-type connectedClusters --yes
    az connectedk8s delete -n ${CLUSTER} -g ${GROUPE} --yes
    az group delete --name ${GROUPE} --yes --no-wait
────────────────────────────────────────────────────────────
TXT
