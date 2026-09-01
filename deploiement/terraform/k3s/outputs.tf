locals {
  ip_controle = azurerm_public_ip.noeud["controle"].ip_address
  ip_charge   = azurerm_public_ip.noeud["charge"].ip_address
}

output "ip_controle" {
  description = "Adresse publique du nœud de contrôle."
  value       = local.ip_controle
}

output "ip_charge" {
  description = "Adresse publique du nœud de charge — c'est elle qui sert la plateforme."
  value       = local.ip_charge
}

output "adresse_plateforme" {
  description = "Adresse à ouvrir dans un navigateur une fois le déploiement terminé."
  value       = "http://${local.ip_charge}"
}

# L'inventaire Ansible est produit par Terraform plutôt qu'écrit à la main.
# Recopier deux adresses semble anodin, mais c'est exactement le geste qu'on
# oublie de refaire après un `destroy` suivi d'un `apply` — et l'on passe
# alors une heure à comprendre pourquoi la configuration s'applique à des
# machines qui n'existent plus.
output "inventaire_ansible" {
  description = "Inventaire à écrire dans deploiement/ansible/inventaire.ini"
  value       = <<-INI
    [controle]
    vm-controle ansible_host=${local.ip_controle} adresse_privee=10.0.1.10

    [charge]
    vm-charge ansible_host=${local.ip_charge} adresse_privee=10.0.1.11

    [cluster:children]
    controle
    charge

    [cluster:vars]
    ansible_user=${var.utilisateur}
    ansible_python_interpreter=/usr/bin/python3
    ansible_ssh_common_args='-o StrictHostKeyChecking=accept-new'
  INI
}

output "commande_destruction" {
  description = "À exécuter une fois les captures prises : les machines sont facturées à l'heure."
  value       = "terraform destroy -auto-approve"
}
