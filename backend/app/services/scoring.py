"""Moteur de score hybride : règles métiers et proximité sémantique.

Le calcul suit les conventions des systèmes de suivi des candidatures :

  * les critères de qualification se répartissent entre exigences
    **obligatoires** — dont l'absence disqualifie — et compétences
    **souhaitées**, qui valorisent le profil sans être bloquantes ;
  * tout écartement conserve son motif exact, condition de l'explicabilité ;
  * le score final reste sur 100, quelles que soient les composantes
    disponibles, afin que les candidatures demeurent comparables.

Règle RG-01 : score < 50 -> écartée (conservée, repêchable) ;
parmi les >= 50, les 10 meilleures forment la shortlist.
"""

SEUIL_RETENU = 50
PLAFOND_TOP = 10

# Ponderation des composantes du score (total = 100)
POIDS_COMPETENCES = 35   # competences obligatoires
POIDS_SOUHAITEES = 10    # competences appreciees
POIDS_SEMANTIQUE = 25
POIDS_EXPERIENCE = 20
POIDS_DIPLOME = 10

NIVEAUX_DIPLOME = {"bac": 0, "bac+2": 2, "bac+3": 3, "bac+5": 5, "doctorat": 8}


def _diplome_suffisant(candidat, requis):
    if not requis:
        return True
    a = NIVEAUX_DIPLOME.get((candidat or "").lower(), -1)
    b = NIVEAUX_DIPLOME.get(requis.lower(), 0)
    return a >= b


def calculer_score(profil, offre, similarite_semantique=None):
    """Compare un profil extrait du CV à une offre.

    profil : dict {skills: [str], experience_years: int, degree: str}
    similarite_semantique : proximité [0, 1] entre le texte du CV et celui de
        l'offre, ou None lorsqu'elle n'a pas pu être calculée (saisie manuelle
        du profil, ou texte du CV indisponible).

    Retourne (score, details) — details sert a l'explicabilite cote interface.
    """
    requises = [s.lower() for s in (offre.required_skills or [])]
    souhaitees = [s.lower() for s in (getattr(offre, "preferred_skills", None) or [])]
    possedees = [s.lower() for s in profil.get("skills", [])]

    trouvees = [s for s in requises if s in possedees]
    manquantes = [s for s in requises if s not in possedees]
    bonus_trouvees = [s for s in souhaitees if s in possedees]

    experience = profil.get("experience_years", 0) or 0
    diplome = profil.get("degree")

    # 1. Criteres eliminatoires : tout rejet est trace avec son motif exact.
    #    Une competence obligatoire absente disqualifie, conformement a la
    #    pratique des ATS qui distinguent exigences et preferences.
    eliminatoires = []
    if offre.min_experience_years and experience < offre.min_experience_years:
        eliminatoires.append(
            f"Expérience {experience} an(s) < {offre.min_experience_years} an(s) requis"
        )
    if offre.min_degree and not _diplome_suffisant(diplome, offre.min_degree):
        eliminatoires.append(
            f"Diplôme {diplome or 'non renseigné'} < {offre.min_degree} requis"
        )
    if manquantes:
        eliminatoires.append(
            "Compétence(s) obligatoire(s) absente(s) : " + ", ".join(manquantes)
        )

    # 2. Composantes du score
    #
    #    Le poids d'une composante indisponible est redistribue sur les
    #    competences obligatoires, afin que le total reste sur 100 et que les
    #    candidatures demeurent comparables entre elles.
    poids_competences = POIDS_COMPETENCES
    if similarite_semantique is None:
        poids_competences += POIDS_SEMANTIQUE
    if not souhaitees:
        poids_competences += POIDS_SOUHAITEES

    part_competences = (
        (len(trouvees) / len(requises) * poids_competences) if requises else poids_competences
    )
    part_souhaitees = (
        (len(bonus_trouvees) / len(souhaitees) * POIDS_SOUHAITEES) if souhaitees else 0.0
    )
    part_semantique = (
        (similarite_semantique or 0.0) * POIDS_SEMANTIQUE
        if similarite_semantique is not None
        else 0.0
    )
    if offre.min_experience_years:
        ratio = min(experience / offre.min_experience_years, 1.5) / 1.5
    else:
        ratio = 1.0
    part_experience = ratio * POIDS_EXPERIENCE
    part_diplome = POIDS_DIPLOME if _diplome_suffisant(diplome, offre.min_degree) else 0

    score = round(
        part_competences + part_souhaitees + part_semantique + part_experience + part_diplome
    )
    if eliminatoires:
        score = min(score, 45)  # ecarte par regle metier
    score = max(0, min(100, score))

    composantes = [
        {
            "libelle": "Compétences obligatoires",
            "valeur": round(part_competences),
            "max": round(poids_competences),
        },
    ]
    if souhaitees:
        composantes.append(
            {
                "libelle": "Compétences souhaitées",
                "valeur": round(part_souhaitees),
                "max": POIDS_SOUHAITEES,
            }
        )
    if similarite_semantique is not None:
        composantes.append(
            {
                "libelle": "Proximité sémantique CV / offre",
                "valeur": round(part_semantique),
                "max": POIDS_SEMANTIQUE,
            }
        )
    composantes += [
        {
            "libelle": "Années d'expérience",
            "valeur": round(part_experience),
            "max": POIDS_EXPERIENCE,
        },
        {"libelle": "Niveau de diplôme", "valeur": part_diplome, "max": POIDS_DIPLOME},
    ]

    details = {
        "competences_trouvees": trouvees,
        "competences_manquantes": manquantes,
        "competences_souhaitees_trouvees": bonus_trouvees,
        "competences_souhaitees_manquantes": [s for s in souhaitees if s not in possedees],
        "eliminatoires": eliminatoires,
        "composantes": composantes,
        "version_moteur": "ats-3.0",
    }
    return score, details


def appliquer_regle_top(candidatures):
    """Sépare les candidatures selon la règle RG-01."""
    retenues = [c for c in candidatures if (c.score or 0) >= SEUIL_RETENU]
    retenues.sort(key=lambda c: c.score or 0, reverse=True)
    return {
        "top": retenues[:PLAFOND_TOP],
        "ecartees": [c for c in candidatures if (c.score or 0) < SEUIL_RETENU],
    }
