# Infrastructure du déploiement de démonstration.
#
# Ce fichier décrit ce que `deploiement/aci/deployer.sh` créait par une suite
# de commandes. La différence n'est pas cosmétique :
#
#   * le script sait créer, il ne sait ni comparer ni détruire proprement ;
#     Terraform tient un état et calcule la différence entre ce qui est
#     décrit et ce qui existe, ce qui rend l'opération rejouable ;
#   * le script décrit implicitement l'infrastructure au fil de ses appels ;
#     ici elle est écrite noir sur blanc, relisible sans exécuter quoi que
#     ce soit ;
#   * `terraform destroy` libère l'ensemble d'un coup, ce qui compte quand
#     l'abonnement est un crédit étudiant que rien ne réapprovisionne.
#
# Le script d'origine est conservé : il reste le chemin le plus court pour
# une démonstration depuis le Cloud Shell, sans installer Terraform.

locals {
  # Un suffixe aléatoire seulement si aucune étiquette n'a été imposée.
  etiquette_dns = var.etiquette_dns != "" ? var.etiquette_dns : "skillseek-${random_string.dns.result}"
  fqdn          = "${local.etiquette_dns}.${var.region}.azurecontainer.io"

  # Les quatre conteneurs partagent une pile réseau : ils se joignent donc
  # par 127.0.0.1, et non par un nom de service comme sous Compose. C'est la
  # seule différence de fond entre cette description et l'environnement de
  # développement.
  base_url = "postgresql://skillseek:${random_password.base.result}@127.0.0.1:5432/skillseek"

  # Le service applicatif attend la base, applique les migrations, installe
  # les rôles puis le jeu de démonstration, et seulement ensuite se met à
  # écouter. Sans cette attente la première migration échouerait : dans un
  # groupe de conteneurs, tous démarrent ensemble et aucun ordre n'est
  # garanti.
  lancement = join(" ", [
    "for i in $(seq 1 90); do",
    "python -c \"import socket; socket.create_connection(('127.0.0.1', 5432), 2)\" 2>/dev/null && break;",
    "sleep 2; done;",
    "flask db upgrade && flask seed && flask demo --reset;",
    "exec flask run --host=0.0.0.0 --port=5000",
  ])
}

resource "random_string" "dns" {
  length  = 6
  special = false
  upper   = false
}

# Trois secrets neufs à chaque création. Ceux de `.env.example` sont publics
# par construction : les reprendre sur une machine exposée reviendrait à
# publier les clés de signature des jetons.
#
# Ces valeurs sont écrites dans l'état Terraform. C'est la raison pour
# laquelle cet état ne doit jamais rester en clair sur un poste partagé ni
# être versionné — voir `backend.tf`.
resource "random_password" "base" {
  length  = 32
  special = false
}

resource "random_password" "cle_secrete" {
  length  = 48
  special = false
}

resource "random_password" "cle_jwt" {
  length  = 48
  special = false
}

resource "azurerm_resource_group" "principal" {
  name     = var.groupe
  location = var.region
  tags     = var.marqueurs
}

resource "azurerm_container_group" "skillseek" {
  name                = var.nom
  resource_group_name = azurerm_resource_group.principal.name
  location            = azurerm_resource_group.principal.location
  os_type             = "Linux"

  ip_address_type = "Public"
  dns_name_label  = local.etiquette_dns

  # Un conteneur qui s'arrête sans erreur ne doit pas être relancé : la
  # migration se termine normalement, et « Always » la rejouerait en boucle.
  restart_policy = "OnFailure"

  tags = var.marqueurs

  # Un seul port franchit la frontière du groupe. Le déclarer explicitement
  # plutôt que de laisser le fournisseur ouvrir tout ce qu'un conteneur
  # expose évite qu'un port ajouté par mégarde se retrouve public.
  exposed_port {
    port     = 80
    protocol = "TCP"
  }

  container {
    name   = "db"
    image  = "postgres:16-alpine"
    cpu    = "0.5"
    memory = "1.5"

    environment_variables = {
      POSTGRES_USER = "skillseek"
      POSTGRES_DB   = "skillseek"
      # Le répertoire est un sous-dossier du point de montage : Postgres
      # refuse de s'initialiser dans un répertoire qui n'est pas vide.
      PGDATA = "/var/lib/postgresql/data/pgdata"
    }

    secure_environment_variables = {
      POSTGRES_PASSWORD = random_password.base.result
    }
  }

  container {
    name     = "backend"
    image    = "ghcr.io/${var.depot_images}/backend:${var.etiquette}"
    cpu      = "2.0"
    memory   = "8.0"
    commands = ["/bin/sh", "-c", local.lancement]

    environment_variables = {
      FLASK_ENV = "production"
      # Pas de FLASK_APP : depuis /app, Flask découvre seul le paquet `app`
      # et sa fabrique `create_app`. Désigner un fichier inexistant ferait
      # échouer le démarrage.
      FRONTEND_ORIGIN      = "http://${local.fqdn}"
      GIT_SHA              = var.etiquette
      LOGIN_MAX_ECHECS     = "5"
      LOGIN_VERROU_MINUTES = "10"
    }

    # « secure » signifie que la valeur n'est plus lisible ensuite, ni par
    # le portail ni par `az container show`. C'est le seul endroit où les
    # identifiants doivent apparaître.
    secure_environment_variables = {
      DATABASE_URL   = local.base_url
      SECRET_KEY     = random_password.cle_secrete.result
      JWT_SECRET_KEY = random_password.cle_jwt.result
    }
  }

  container {
    name   = "frontend"
    image  = "ghcr.io/${var.depot_images}/frontend:${var.etiquette}"
    cpu    = "0.5"
    memory = "1.5"

    environment_variables = {
      PORT     = "3000"
      HOSTNAME = "0.0.0.0"
    }
  }

  # Seul le proxy expose un port vers l'extérieur. Le service applicatif et
  # la base ne sont joignables que depuis la pile réseau partagée : c'est ce
  # qui évite d'avoir à ouvrir 5000 et 5432 sur Internet.
  container {
    name   = "proxy"
    image  = "nginx:1.27-alpine"
    cpu    = "0.5"
    memory = "1.0"

    ports {
      port     = 80
      protocol = "TCP"
    }

    # La configuration du proxy est montée comme un volume secret plutôt que
    # copiée dans une image : elle change plus souvent que le code, et la
    # reconstruire à chaque ajustement d'en-tête serait disproportionné.
    volume {
      name       = "configuration-proxy"
      mount_path = "/etc/nginx/conf.d"
      read_only  = true

      secret = {
        "default.conf" = base64encode(file("${path.module}/../aci/nginx.conf"))
      }
    }
  }
}
