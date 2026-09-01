# Cluster Kubernetes infogéré — versions épinglées.
#
# Ce module est séparé de celui du déploiement Container Instances, et
# volontairement. Les deux cibles n'ont pas la même durée de vie : le groupe
# de conteneurs sert la démonstration en continu, le cluster est créé pour
# quelques heures puis détruit. Les mêler dans un seul état obligerait à
# détruire l'un pour libérer l'autre.

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.14"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.abonnement
}
