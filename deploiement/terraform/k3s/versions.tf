# Cluster k3s sur machines Azure — versions épinglées.
#
# Module séparé de celui du groupe de conteneurs, et volontairement : les
# deux cibles n'ont pas la même durée de vie. Le groupe de conteneurs sert
# la démonstration en continu ; le cluster est créé pour quelques heures puis
# détruit. Les mêler dans un seul état obligerait à détruire l'un pour
# libérer l'autre.

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
