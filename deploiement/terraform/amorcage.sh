#!/usr/bin/env bash
#
# Crée le stockage de l'état Terraform.
#
# Cette étape ne peut pas être décrite par Terraform lui-même : il faudrait
# un état pour créer l'endroit où ranger l'état. C'est le seul endroit du
# déploiement où des commandes impératives restent justifiées.
#
#   bash deploiement/terraform/amorcage.sh
#
# À n'exécuter qu'une fois. La suppression du groupe applicatif ne touche
# pas à ce groupe-ci, c'est l'objet de la séparation.

set -euo pipefail

GROUPE_ETAT="${GROUPE_ETAT:-SkillSeek-tfstate}"
REGION="${REGION:-germanywestcentral}"
COMPTE="${COMPTE:-skillseektfstate}"
CONTENEUR="${CONTENEUR:-tfstate}"

echo "→ Groupe de ressources dédié à l'état"
az group create --name "$GROUPE_ETAT" --location "$REGION" --output none

echo "→ Compte de stockage"
# Redondance locale : trois copies dans un même centre de données. L'état
# d'un déploiement de démonstration ne justifie pas une réplication
# géographique, qui coûte davantage.
#
# L'accès public au conteneur est refusé, et l'authentification par clé
# partagée désactivée : seule l'identité Azure de l'appelant ouvre l'objet.
az storage account create \
  --name "$COMPTE" \
  --resource-group "$GROUPE_ETAT" \
  --location "$REGION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --min-tls-version TLS1_2 \
  --allow-blob-public-access false \
  --allow-shared-key-access false \
  --output none

echo "→ Attribution du rôle d'accès aux données"
# Sans ce rôle, la commande suivante échoue : désactiver la clé partagée
# signifie que même le propriétaire de l'abonnement doit passer par RBAC
# pour lire un objet.
identite="$(az ad signed-in-user show --query id -o tsv)"
abonnement="$(az account show --query id -o tsv)"
az role assignment create \
  --assignee "$identite" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/${abonnement}/resourceGroups/${GROUPE_ETAT}/providers/Microsoft.Storage/storageAccounts/${COMPTE}" \
  --output none

echo "→ Attente de la propagation du rôle (jusqu'à une minute)"
sleep 45

echo "→ Conteneur d'objets"
az storage container create \
  --name "$CONTENEUR" \
  --account-name "$COMPTE" \
  --auth-mode login \
  --output none

cat <<TXT

────────────────────────────────────────────────────────────
  Stockage de l'état prêt.

  Décommentez le bloc « backend » de backend.tf, puis :

    cd deploiement/terraform
    export ARM_SUBSCRIPTION_ID="${abonnement}"
    terraform init -migrate-state

  Vérifiez que le compte est bien « ${COMPTE} » dans backend.tf :
  un nom de compte de stockage est unique dans tout Azure, celui-ci
  peut donc être déjà pris et avoir été ajusté.
────────────────────────────────────────────────────────────
TXT
