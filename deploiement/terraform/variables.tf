# Paramètres du déploiement.
#
# Tout ce qui distingue un environnement d'un autre est ici, et nulle part
# ailleurs. C'est la condition pour que `main.tf` décrive une architecture
# plutôt qu'une instance particulière.

variable "abonnement" {
  description = "Identifiant de l'abonnement Azure visé."
  type        = string
  # Aucune valeur par défaut : un identifiant d'abonnement écrit dans le
  # dépôt finit toujours par être le mauvais.
}

variable "groupe" {
  description = "Nom du groupe de ressources."
  type        = string
  default     = "SkillSeek-demo"
}

variable "region" {
  description = <<-TXT
    Région Azure.

    L'abonnement académique utilisé n'accorde aucun quota de processeurs
    virtuels sur les familles de machines proposées dans les régions qu'il
    autorise. Le service Container Instances relève d'un quota distinct,
    lui disponible : c'est ce qui a déterminé le choix de la cible, et non
    une préférence de latence.
  TXT
  type        = string
  default     = "germanywestcentral"
}

variable "nom" {
  description = "Nom du groupe de conteneurs."
  type        = string
  default     = "skillseek"
}

variable "depot_images" {
  description = "Chemin du dépôt d'images sur GHCR, en minuscules — le registre l'impose."
  type        = string
  default     = "aymb1303/skillseek-ai"
}

variable "etiquette" {
  description = <<-TXT
    Étiquette des images à déployer : `latest`, une version (`v1.0.0`) ou
    une empreinte de commit (`sha-abc1234`).

    C'est le seul paramètre que l'on change pour un retour arrière :
    remettre en ligne une version précédente est la même opération qu'un
    déploiement, avec une autre valeur ici.
  TXT
  type        = string
  default     = "latest"

  validation {
    condition     = can(regex("^(latest|v[0-9]+\\.[0-9]+(\\.[0-9]+)?|sha-[0-9a-f]{7,})$", var.etiquette))
    error_message = "Étiquette attendue : latest, vX.Y[.Z] ou sha-<empreinte>."
  }
}

variable "etiquette_dns" {
  description = <<-TXT
    Préfixe DNS public. Doit être unique dans la région ; laisser vide pour
    qu'un suffixe aléatoire soit tiré, ce qui évite la collision avec un
    groupe créé précédemment et pas encore libéré.
  TXT
  type        = string
  default     = ""
}

variable "marqueurs" {
  description = "Étiquettes de ressources, utiles pour rattacher une dépense à son objet."
  type        = map(string)
  default = {
    projet      = "SkillSeek AI"
    environment = "demonstration"
    gestion     = "terraform"
  }
}
