# Cluster Kubernetes infogéré.
#
# Ce que ce module ajoute par rapport au groupe de conteneurs déjà déployé :
# un ordonnanceur qui replace un conteneur mort, des mises à jour
# progressives sans coupure, une mise à l'échelle automatique, et un
# cloisonnement réseau appliqué par le cluster lui-même. Container Instances
# n'offre aucun de ces quatre points.
#
# Ce qu'il ne prétend pas être : un cluster de production. Un seul nœud, donc
# aucune tolérance à la panne matérielle. C'est assumé, et écrit dans le
# rapport.

resource "azurerm_resource_group" "aks" {
  name     = var.groupe
  location = var.region
  tags     = var.marqueurs
}

resource "azurerm_kubernetes_cluster" "skillseek" {
  name                = var.nom
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  dns_prefix          = var.nom
  kubernetes_version  = var.version_kubernetes

  # Palier gratuit : le plan de contrôle n'est pas facturé, et son
  # engagement de disponibilité n'a pas de sens pour un cluster qui vit
  # quelques heures. Seul le nœud est payant.
  sku_tier = "Free"

  default_node_pool {
    name       = "systeme"
    node_count = 1
    vm_size    = var.taille_noeud

    # Disque géré plutôt qu'éphémère : le disque éphémère du système
    # d'exploitation est plus rapide, mais la taille retenue n'offre pas le
    # cache local qu'il exige. Le demander ferait échouer la création avec
    # un message qui ne l'explique pas.
    os_disk_type    = "Managed"
    os_disk_size_gb = 64

    # L'image du service applicatif pèse près de quatre gigaoctets ; la
    # place doit être prévue, sous peine de voir le nœud expulser des pods
    # pour manque d'espace au premier tirage.
    node_labels = {
      "role" = "applicatif"
    }
  }

  # Identité gérée : le cluster obtient lui-même les jetons dont il a besoin
  # pour créer des disques et des adresses publiques. C'est la même logique
  # que la fédération d'identité côté chaîne de livraison — pas de secret à
  # déposer, donc pas de secret à faire tourner ni à révoquer.
  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
    # Le greffon réseau par défaut n'applique pas les règles de
    # cloisonnement. Sans cette ligne, les trois politiques réseau décrites
    # dans `k8s/base` seraient acceptées par le serveur d'API puis
    # ignorées — une protection annoncée et inexistante, ce qui est pire
    # que pas de protection du tout.
    network_policy = "azure"
  }

  tags = var.marqueurs

  lifecycle {
    ignore_changes = [
      # Le nombre de nœuds peut être ajusté à la main pendant une
      # démonstration ; Terraform ne doit pas le ramener à sa valeur
      # décrite au prochain passage.
      default_node_pool[0].node_count,
    ]
  }
}
