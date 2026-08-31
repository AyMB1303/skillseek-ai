# Versions épinglées.
#
# Un fichier d'infrastructure sans contrainte de version n'est reproductible
# qu'à la date où il a été écrit : le fournisseur évolue, ses attributs
# changent de nom ou de valeur par défaut, et la même description produit
# alors une infrastructure différente. C'est précisément ce que l'on cherche
# à éviter en la décrivant.

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.14"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}

  # L'abonnement est fourni par la variable d'environnement
  # ARM_SUBSCRIPTION_ID, jamais écrit dans le dépôt.
  subscription_id = var.abonnement
}
