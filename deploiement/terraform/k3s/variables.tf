variable "abonnement" {
  description = "Identifiant de l'abonnement Azure."
  type        = string
}

variable "groupe" {
  description = "Groupe de ressources du cluster."
  type        = string
  default     = "SkillSeek-cluster"
}

variable "region" {
  description = <<-TXT
    Région Azure.

    Ni germanywestcentral, où tourne pourtant le groupe de conteneurs, ni
    aucune des sept autres régions proches. La création y échoue sur une
    restriction de capacité — « SkuNotAvailable » — qui n'est ni un quota ni
    une exclusion de service : Azure n'a tout simplement pas de machines de
    ces familles à fournir, pour ce type d'abonnement, à cet endroit.

    C'est le troisième obstacle rencontré sur ce déploiement, et le seul qui
    ne se lise pas dans une politique : il faut interroger la disponibilité
    réelle par région, ce que fait `az vm list-skus` en regardant le champ
    des restrictions.

    swedencentral et polandcentral sont les deux seules à répondre.
  TXT
  type        = string
  default     = "swedencentral"
}

variable "taille_controle" {
  description = <<-TXT
    Machine du nœud de contrôle : serveur k3s, agents de rattachement.

    Le dimensionnement n'est pas libre. L'abonnement académique plafonne le
    total régional à six cœurs virtuels, et n'accorde de quota qu'aux
    familles antérieures — Basv2 en compte dix, BS quatre, DSv3 quatre. Les
    générations v5 à v7, celles que le portail propose par défaut, sont
    toutes à zéro : c'est ce qui explique l'échec des premières tentatives.

    Deux cœurs suffisent ici : ce nœud n'exécute aucune charge applicative,
    il est marqué pour les refuser.
  TXT
  type        = string
  default     = "Standard_B2as_v2"
}

variable "taille_charge" {
  description = <<-TXT
    Machine du nœud de charge : la plateforme y tourne.

    Quatre cœurs et seize gigaoctets. La mémoire commande le choix : le
    service applicatif en réserve trois à lui seul, son image en pèse près
    de quatre, et il doit rester de quoi placer une seconde réplique quand
    la mise à l'échelle automatique se déclenche.

    Deux plus quatre égale six, soit exactement le plafond régional. Rien
    ne peut être ajouté sans retirer autre chose, et c'est assumé.
  TXT
  type        = string
  default     = "Standard_B4as_v2"
}

variable "utilisateur" {
  description = "Compte administrateur des machines."
  type        = string
  default     = "aymen"
}

variable "chemin_cle_publique" {
  description = <<-TXT
    Chemin de la clé publique SSH autorisée sur les machines.

    Seule la partie publique est lue. La clé privée ne quitte jamais le
    poste et n'apparaît ni dans ce dépôt, ni dans l'état Terraform, ni dans
    aucun journal d'exécution.

    Si vous n'en avez pas : ssh-keygen -t ed25519

    Aucune valeur par défaut, et pour deux raisons. La première tient à
    l'usage : le chemin d'une clé varie d'un poste à l'autre, et une valeur
    par défaut qui tombe juste une fois sur deux est pire qu'une absence de
    valeur. La seconde tient à l'outillage : `terraform validate` évalue les
    expressions dont tous les termes sont connus, et lirait donc un fichier
    absent de l'exécuteur de la chaîne d'intégration, faisant échouer une
    vérification qui n'a rien à voir avec le contenu du module.
  TXT
  type        = string
}

variable "adresse_administration" {
  description = <<-TXT
    Adresse publique autorisée à ouvrir une session SSH, en notation CIDR.

    Laisser vide fait échouer volontairement la validation : ouvrir le port
    d'administration à l'Internet entier est le défaut de configuration le
    plus banal, et il ne doit pas pouvoir se produire par omission.

    Relevez la vôtre : curl -s ifconfig.me
  TXT
  type        = string

  validation {
    condition     = can(cidrnetmask(var.adresse_administration)) && var.adresse_administration != "0.0.0.0/0"
    error_message = "Attendu : une adresse en notation CIDR, par exemple 41.248.10.5/32. L'ouverture à 0.0.0.0/0 est refusée."
  }
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
