"""Retour factuel adressé au candidat sur sa candidature.

Une décision prise avec l'aide d'un traitement automatisé doit pouvoir être
expliquée à la personne qu'elle concerne. C'est une exigence du règlement
général sur la protection des données, reprise par le règlement européen sur
l'intelligence artificielle, et c'est aussi la simple contrepartie de ce que
la plateforme offre déjà au recruteur : elle lui justifie chaque point
attribué, elle ne peut pas laisser le candidat devant un refus muet.

Trois règles gouvernent ce module.

**La note n'est jamais communiquée.** Elle relève de l'appréciation interne du
recruteur, et un chiffre sans son barème invite au malentendu bien plus qu'il
n'éclaire. Ce sont les faits qui sont restitués : quelles compétences
manquaient, quelle expérience était attendue.

**Seuls les critères objectifs sont exposés.** La proximité sémantique ou
l'avis du modèle appris ne se traduisent pas en conseil actionnable. Dire à
quelqu'un « votre CV ressemblait peu à l'offre » ne lui apprend rien qu'il
puisse corriger.

**Rien n'est dit qui concerne un autre candidat.** Le classement, le rang, le
nombre de postulants : ces informations appartiennent au recruteur.
"""

# Le retour n'est produit qu'une fois la decision prise. Avant, il laisserait
# croire au candidat qu'il est deja ecarte alors que son dossier est en cours.
STATUTS_AVEC_RETOUR = ("rejected",)


def construire(candidature):
    """Retour destiné au candidat, ou None s'il n'y a rien à dire.

    Retourne un dictionnaire prêt à afficher, sans note ni information
    relative aux autres candidatures.
    """
    if candidature.status not in STATUTS_AVEC_RETOUR:
        return None

    details = candidature.score_details or {}

    # Un document illisible n'est pas un motif de refus imputable au candidat,
    # mais il est utile qu'il le sache : c'est la seule chose qu'il puisse
    # corriger dans ce cas.
    if details.get("statut") in ("extraction_echouee", "analyse_indisponible"):
        return {
            "lisible": False,
            "message": (
                "Votre curriculum vitæ n'a pas pu être lu automatiquement. "
                "Un document au format PDF contenant du texte — et non une "
                "image numérisée — sera mieux exploité lors d'une prochaine "
                "candidature."
            ),
            "points": [],
        }

    points = []

    manquantes = details.get("competences_manquantes") or []
    if manquantes:
        points.append(
            "Compétences attendues et non identifiées dans votre CV : "
            + ", ".join(manquantes)
            + "."
        )

    trouvees = details.get("competences_trouvees") or []
    if trouvees:
        points.append(
            "Compétences bien identifiées : " + ", ".join(trouvees) + "."
        )

    # Les criteres eliminatoires sont deja rediges en langage clair par le
    # moteur ; on ne retient que ceux qui portent sur l'experience ou le
    # diplome, les competences etant traitees ci-dessus.
    for motif in details.get("eliminatoires") or []:
        if motif.startswith(("Expérience", "Diplôme")):
            points.append(motif + ".")

    for reserve in details.get("reserves") or []:
        points.append(reserve + ".")

    if not points:
        return {
            "lisible": True,
            "message": (
                "Votre candidature n'a pas été retenue pour ce poste. Le profil "
                "recherché ne correspondait pas suffisamment au vôtre sur les "
                "critères de l'offre."
            ),
            "points": [],
        }

    return {
        "lisible": True,
        "message": (
            "Votre candidature n'a pas été retenue. Voici les éléments objectifs "
            "relevés lors de l'analyse de votre CV au regard de cette offre."
        ),
        "points": points,
        "avertissement": (
            "Cette analyse porte sur ce que le document laissait apparaître, "
            "et sur cette offre uniquement. Elle ne préjuge pas de vos "
            "compétences réelles."
        ),
    }
