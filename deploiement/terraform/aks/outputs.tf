output "nom_cluster" {
  description = "Nom du cluster, à passer à la commande de récupération des accès."
  value       = azurerm_kubernetes_cluster.skillseek.name
}

output "groupe" {
  description = "Groupe de ressources du cluster."
  value       = azurerm_resource_group.aks.name
}

output "commande_acces" {
  description = "Commande à exécuter pour configurer kubectl sur ce cluster."
  value = join(" ", [
    "az aks get-credentials",
    "--resource-group", azurerm_resource_group.aks.name,
    "--name", azurerm_kubernetes_cluster.skillseek.name,
    "--overwrite-existing",
  ])
}

output "commande_destruction" {
  description = "À exécuter une fois les captures prises. Le nœud est facturé à l'heure."
  value       = "terraform destroy -auto-approve"
}

# Le fichier de configuration d'accès n'est volontairement pas exposé en
# sortie. Il contient un certificat client qui ouvre le cluster en
# administrateur, et une sortie Terraform se retrouve en clair dans l'état,
# dans les journaux d'exécution et dans tout ce qui interroge le module.
# `az aks get-credentials` le récupère à la demande, ce qui est le bon
# moment pour un secret : celui où on s'en sert.
