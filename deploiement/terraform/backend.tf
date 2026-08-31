# Emplacement de l'état Terraform.
#
# L'état est le fichier qui associe chaque ressource décrite ici à la
# ressource réelle qui lui correspond dans Azure. Sans lui, Terraform ne sait
# plus ce qu'il a créé et recrée tout. Il contient donc aussi les valeurs
# calculées, y compris les trois secrets tirés au hasard dans `main.tf`.
#
# Deux raisons de le sortir du poste de travail :
#
#   1. une seule source de vérité, accessible depuis n'importe quelle
#      machine — sinon un déploiement lancé depuis un autre poste croit
#      partir de zéro ;
#   2. un verrouillage : Azure Blob Storage pose un bail sur l'objet, ce qui
#      bloque un second `terraform apply` lancé en parallèle tant que le
#      premier n'a pas rendu la main. Deux exécutions simultanées sur le
#      même état le corrompent.
#
# Le compte de stockage est volontairement placé dans un groupe de
# ressources distinct : un `terraform destroy` de l'infrastructure
# applicative ne doit pas pouvoir supprimer l'état qui la décrit.
#
# Pour activer : exécuter `bash amorcage.sh`, puis décommenter le bloc
# ci-dessous et lancer `terraform init -migrate-state`.
#
# terraform {
#   backend "azurerm" {
#     resource_group_name  = "SkillSeek-tfstate"
#     storage_account_name = "skillseektfstate"
#     container_name       = "tfstate"
#     key                  = "demonstration.tfstate"
#
#     # L'accès passe par l'identité Azure de celui qui exécute la commande,
#     # et non par une clé de compte de stockage. Une clé partagée est un
#     # secret statique de plus à faire circuler, donc à perdre.
#     use_azuread_auth = true
#   }
# }
