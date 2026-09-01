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

    ⚠ CE MODULE N'A PAS PU ÊTRE APPLIQUÉ. Il décrit ce qui serait déployé,
    il est vérifié par la chaîne d'intégration, mais aucun cluster n'en est
    issu. La raison est instructive et tient en deux constats qui se
    contredisent.

    Le quota d'abord : l'abonnement académique plafonne le total régional à
    six cœurs virtuels, et n'en accorde qu'aux familles antérieures — Basv2,
    BS, DSv3, DASv4. Les générations v5, v6 et v7 sont toutes à zéro.

    L'offre du service ensuite : AKS tient sa propre liste de tailles
    acceptées, indépendante du quota, et cette liste ne contient que des
    générations récentes — d*s_v7, d*ps_v6, e*s_v7, f*as_v6, l*s_v4.

    L'intersection est vide, et elle l'est dans les neuf régions autorisées.
    Ce que l'abonnement permet de créer, le service refuse ; ce que le
    service accepte, l'abonnement ne permet pas de créer. Le déploiement a
    donc été conduit sur un cluster local, avec ces mêmes manifestes.

    La valeur ci-dessous est celle qui serait retenue si le quota s'ouvrait :
    famille Basv2, quatre cœurs sur les six disponibles, et seize gigaoctets
    de mémoire — nécessaires, le service applicatif en réservant trois à lui
    seul pour une image qui en pèse près de quatre.
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
