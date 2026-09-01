variable "abonnement" {
  description = "Identifiant de l'abonnement Azure."
  type        = string
}

variable "groupe" {
  description = "Groupe de ressources dédié au cluster, distinct de celui du groupe de conteneurs."
  type        = string
  default     = "SkillSeek-aks"
}

variable "region" {
  description = "Région Azure."
  type        = string
  default     = "germanywestcentral"
}

variable "nom" {
  description = "Nom du cluster."
  type        = string
  default     = "skillseek-aks"
}

variable "taille_noeud" {
  description = <<-TXT
    Taille de la machine du nœud de calcul.

    Le choix n'est pas libre : l'abonnement académique plafonne le total
    régional à six cœurs virtuels, et n'accorde de quota qu'aux familles
    antérieures. Les tailles proposées par défaut dans le portail — les
    générations v5 et v6 — sont toutes à zéro, ce qui explique l'échec des
    premières tentatives de juillet.

    `Standard_B4as_v2` relève de la famille Basv2, où le quota est de dix,
    et consomme quatre cœurs sur les six disponibles. Ses seize gigaoctets
    de mémoire sont nécessaires : le service applicatif en réserve trois à
    lui seul, et son image en pèse près de quatre.
  TXT
  type        = string
  default     = "Standard_B4as_v2"
}

variable "version_kubernetes" {
  description = "Version du plan de contrôle. Laisser vide pour la version par défaut de la région."
  type        = string
  default     = null
}

variable "marqueurs" {
  type = map(string)
  default = {
    projet      = "SkillSeek AI"
    environment = "demonstration"
    gestion     = "terraform"
    duree       = "ephemere"
  }
}
