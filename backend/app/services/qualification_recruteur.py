"""Faisceau d'indices sur une demande de compte recruteur.

Publier une offre engage l'entreprise représentée : c'est pourquoi chaque
compte recruteur passe par la décision d'un administrateur. Encore faut-il
que cette décision repose sur autre chose qu'un nom et une adresse.

**Ce module n'interdit rien**, et ce choix est délibéré. Refuser les
messageries grand public paraît rigoureux ; en pratique, une part importante
des petites entreprises — au Maroc comme ailleurs — recrute depuis une adresse
Gmail. Les bloquer écarterait des recruteurs légitimes pour arrêter des
fraudeurs qui, eux, achèteraient un domaine à dix euros. La contrainte
pénaliserait les honnêtes sans gêner les autres.

Le module se contente donc de **qualifier** : il dit à l'administrateur ce
qu'il regarde, et le laisse trancher. Quatre indices sont produits.
"""
import re

# Messageries grand public les plus repandues. La liste n'a pas vocation a
# etre exhaustive : elle sert a distinguer, pas a filtrer.
MESSAGERIES_GRAND_PUBLIC = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.fr", "hotmail.com",
    "hotmail.fr", "outlook.com", "outlook.fr", "live.com", "live.fr",
    "icloud.com", "me.com", "aol.com", "protonmail.com", "proton.me",
    "gmx.com", "gmx.fr", "yandex.com", "mail.com", "zoho.com",
}

# Domaines jetables : la, le signal est fort. Une adresse temporaire n'a
# aucune raison d'etre utilisee pour un compte professionnel durable.
DOMAINES_JETABLES = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "yopmail.com", "throwawaymail.com", "trashmail.com", "sharklasers.com",
}


def domaine_de(email):
    partie = (email or "").strip().lower().rsplit("@", 1)
    return partie[1] if len(partie) == 2 else ""


def _distance(a, b):
    """Distance d'édition entre deux chaînes, pour repérer les imitations.

    Implémentation directe : les domaines comparés font quelques dizaines de
    caractères, et une dépendance supplémentaire ne se justifierait pas.
    """
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))

    precedente = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        courante = [i]
        for j, cb in enumerate(b, 1):
            courante.append(min(
                precedente[j] + 1,            # suppression
                courante[j - 1] + 1,          # insertion
                precedente[j - 1] + (ca != cb),  # substitution
            ))
        precedente = courante
    return precedente[-1]


def nom_entreprise_probable(domaine):
    """Déduit un nom d'entreprise présentable à partir du domaine.

    « bc-skills.ma » devient « Bc Skills ». Approximatif par nature, cette
    déduction sert à pré-remplir un champ, jamais à remplacer la déclaration
    du recruteur.
    """
    if not domaine or domaine in MESSAGERIES_GRAND_PUBLIC:
        return None
    racine = domaine.rsplit(".", 1)[0]
    # Retire les sous-domaines de second niveau usuels (.co.uk, .com.br)
    racine = re.sub(r"\.(co|com|net|org|gov)$", "", racine)
    racine = racine.rsplit(".", 1)[-1]
    return " ".join(mot.capitalize() for mot in re.split(r"[-_.]", racine) if mot)


def qualifier(utilisateur, autres_comptes):
    """Produit les indices présentés à l'administrateur.

    `autres_comptes` : les comptes déjà connus, servant à situer la demande
    par rapport à ce qui existe.
    """
    domaine = domaine_de(utilisateur.email)
    indices = []

    # --- 1. Nature de l'adresse ---
    if domaine in DOMAINES_JETABLES:
        nature, gravite = "Adresse jetable", "alerte"
        indices.append(
            "Ce domaine fournit des adresses temporaires. Un compte professionnel "
            "durable n'en utilise pas."
        )
    elif domaine in MESSAGERIES_GRAND_PUBLIC:
        nature, gravite = "Messagerie grand public", "attention"
        indices.append(
            "Adresse personnelle et non professionnelle. Fréquent chez les très "
            "petites entreprises : ce n'est pas un motif de refus en soi."
        )
    elif domaine:
        nature, gravite = "Domaine professionnel", "information"
        indices.append(
            f"L'adresse relève du domaine « {domaine} », ce qui suppose un accès "
            f"à la messagerie de cette organisation."
        )
    else:
        nature, gravite = "Adresse illisible", "alerte"

    # --- 2. Antériorité du domaine sur la plateforme ---
    memes = [
        u for u in autres_comptes
        if u.id != utilisateur.id and domaine and domaine_de(u.email) == domaine
    ]
    valides = [u for u in memes if u.status == "active"]
    if valides:
        indices.append(
            f"{len(valides)} compte(s) déjà validé(s) sur ce domaine : "
            + ", ".join(u.full_name for u in valides[:3])
            + "."
        )
    elif memes:
        indices.append(f"{len(memes)} autre(s) demande(s) en attente sur ce domaine.")

    # --- 3. Imitation d'un domaine connu ---
    # Le typosquattage est la fraude classique : « bcskils.ma » pour
    # « bcskills.ma ». Un caractere d'ecart suffit a tromper une lecture rapide.
    if domaine and domaine not in MESSAGERIES_GRAND_PUBLIC:
        connus = {
            domaine_de(u.email) for u in autres_comptes
            if u.status == "active" and domaine_de(u.email) not in MESSAGERIES_GRAND_PUBLIC
        }
        for connu in connus:
            if connu and connu != domaine and _distance(domaine, connu) <= 2:
                gravite = "alerte"
                indices.append(
                    f"Ce domaine ressemble fortement à « {connu} », déjà validé. "
                    f"Vérifiez qu'il ne s'agit pas d'une imitation."
                )
                break

    # --- 4. Cohérence entre l'entreprise déclarée et le domaine ---
    declaree = (utilisateur.company or "").strip()
    deduite = nom_entreprise_probable(domaine)
    if declaree and deduite:
        # Comparaison indulgente : « BC Skills » et « bcskills » concordent.
        a = re.sub(r"[^a-z]", "", declaree.lower())
        b = re.sub(r"[^a-z]", "", deduite.lower())
        if a and b and a not in b and b not in a:
            indices.append(
                f"L'entreprise déclarée (« {declaree} ») ne correspond pas au "
                f"domaine de l'adresse (« {domaine} »)."
            )
            if gravite == "information":
                gravite = "attention"

    return {
        "domaine": domaine,
        "nature": nature,
        "gravite": gravite,
        "entreprise_deduite": deduite,
        "comptes_valides_sur_domaine": len(valides),
        "indices": indices,
        "lecture": (
            "Ces éléments éclairent la décision, ils ne la remplacent pas. "
            "Aucun ne suffit à valider ni à refuser un compte."
        ),
    }
