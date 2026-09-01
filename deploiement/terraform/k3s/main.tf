# Cluster Kubernetes sur machines Azure.
#
# Pourquoi des machines et non le service Kubernetes infogéré : AKS tient sa
# propre liste de tailles acceptées, qui ne contient que des générations
# récentes — précisément celles où l'abonnement académique n'accorde aucun
# quota. L'intersection est vide sur les neuf régions autorisées. Les
# machines ordinaires, elles, relèvent du quota classique, où les familles
# antérieures ont bien des cœurs disponibles.
#
# Le cluster est donc auto-géré : k3s, une distribution Kubernetes complète
# et certifiée, installée par Ansible sur ces deux machines. On y gagne
# d'ailleurs quelque chose — le plan de contrôle n'est pas une boîte noire,
# et sa séparation d'avec les charges applicatives est un choix explicite
# plutôt qu'un réglage du fournisseur.

resource "azurerm_resource_group" "cluster" {
  name     = var.groupe
  location = var.region
  tags     = var.marqueurs
}

# ---------------------------------------------------------------------- #
# Réseau                                                                  #
# ---------------------------------------------------------------------- #

resource "azurerm_virtual_network" "cluster" {
  name                = "reseau-skillseek"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.cluster.location
  resource_group_name = azurerm_resource_group.cluster.name
  tags                = var.marqueurs
}

# Un seul sous-réseau, partagé par les deux machines. Le trafic entre nœuds
# — serveur d'API, communication entre pods — reste ainsi sur le réseau
# interne d'Azure au lieu de ressortir sur Internet, ce qui est à la fois
# plus rapide et une surface d'attaque en moins.
resource "azurerm_subnet" "noeuds" {
  name                 = "noeuds"
  resource_group_name  = azurerm_resource_group.cluster.name
  virtual_network_name = azurerm_virtual_network.cluster.name
  address_prefixes     = ["10.0.1.0/24"]
}

# Seule couche de pare-feu du montage. Trois règles entrantes, pas une de
# plus : tout ce qui n'est pas explicitement autorisé est refusé par la
# règle par défaut d'Azure.
#
# Le trafic entre les deux nœuds n'a besoin d'aucune règle : les échanges
# à l'intérieur d'un même réseau virtuel sont permis par défaut. Ouvrir le
# port du serveur d'API vers l'extérieur serait une faute — il n'est
# joignable que depuis le sous-réseau.
resource "azurerm_network_security_group" "cluster" {
  name                = "securite-skillseek"
  location            = azurerm_resource_group.cluster.location
  resource_group_name = azurerm_resource_group.cluster.name
  tags                = var.marqueurs

  security_rule {
    name                       = "ssh-administration"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    # Restreint à une seule adresse. C'est la mesure la plus simple du
    # montage, et celle qu'on omet le plus souvent.
    source_address_prefix      = var.adresse_administration
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "http-public"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "https-public"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "cluster" {
  subnet_id                 = azurerm_subnet.noeuds.id
  network_security_group_id = azurerm_network_security_group.cluster.id
}

# ---------------------------------------------------------------------- #
# Machines                                                                #
# ---------------------------------------------------------------------- #

locals {
  noeuds = {
    controle = {
      taille  = var.taille_controle
      role    = "controle"
      adresse = "10.0.1.10"
    }
    charge = {
      taille  = var.taille_charge
      role    = "charge"
      adresse = "10.0.1.11"
    }
  }
}

# Adresses publiques statiques : l'arrêt puis le redémarrage d'une machine —
# pratique courante pour économiser un crédit — ne doit demander aucune
# reconfiguration de l'inventaire Ansible, des règles d'accès ni des scripts.
resource "azurerm_public_ip" "noeud" {
  for_each = local.noeuds

  name                = "ip-${each.key}"
  location            = azurerm_resource_group.cluster.location
  resource_group_name = azurerm_resource_group.cluster.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.marqueurs
}

resource "azurerm_network_interface" "noeud" {
  for_each = local.noeuds

  name                = "carte-${each.key}"
  location            = azurerm_resource_group.cluster.location
  resource_group_name = azurerm_resource_group.cluster.name
  tags                = var.marqueurs

  ip_configuration {
    name                          = "interne"
    subnet_id                     = azurerm_subnet.noeuds.id
    private_ip_address_allocation = "Static"
    # Adresse privée fixée : le nœud de charge rejoint le serveur par cette
    # adresse, et une attribution dynamique changerait au redémarrage.
    private_ip_address   = each.value.adresse
    public_ip_address_id = azurerm_public_ip.noeud[each.key].id
  }
}

resource "azurerm_linux_virtual_machine" "noeud" {
  for_each = local.noeuds

  name                = "vm-${each.key}"
  resource_group_name = azurerm_resource_group.cluster.name
  location            = azurerm_resource_group.cluster.location
  size                = each.value.taille
  admin_username      = var.utilisateur

  network_interface_ids = [azurerm_network_interface.noeud[each.key].id]

  # Aucun mot de passe : l'authentification par clé est la seule acceptée.
  # Un mot de passe sur un port ouvert à Internet finit toujours par être
  # essayé, quelle que soit sa longueur.
  disable_password_authentication = true

  admin_ssh_key {
    username   = var.utilisateur
    public_key = file(pathexpand(var.chemin_cle_publique))
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    # L'image du service applicatif pèse près de quatre gigaoctets ; avec
    # le système, les couches intermédiaires et les journaux, trente
    # gigaoctets seraient trop justes et le nœud expulserait des pods pour
    # manque d'espace — un symptôme difficile à relier à sa cause.
    disk_size_gb = each.value.role == "charge" ? 64 : 32
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  tags = merge(var.marqueurs, { role = each.value.role })
}
