# Ce que le déploiement rend à celui qui l'a lancé.

output "adresse" {
  description = "Adresse publique de la plateforme."
  value       = "http://${azurerm_container_group.skillseek.fqdn}"
}

output "ip" {
  description = "Adresse IP publique attribuée au groupe."
  value       = azurerm_container_group.skillseek.ip_address
}

output "version_deployee" {
  description = "Étiquette d'image effectivement en ligne."
  value       = var.etiquette
}

# Volontairement absent : aucune sortie ne restitue les secrets tirés au
# hasard. Ils vivent dans l'état, chiffrés côté Azure une fois posés comme
# variables sécurisées, et personne n'a besoin de les relire — un
# redéploiement en produit de nouveaux.
