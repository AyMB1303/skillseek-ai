"""Moteur de score provisoire (règles métiers).

Version Sprint 2 : système expert seul (critères éliminatoires + correspondance
des compétences). L'analyse NLP et le modèle d'apprentissage viendront enrichir
ce module au Sprint 3 sans changer son interface.

Règle RG-01 : score < 50 -> écartée (conservée, repêchable) ;
parmi les >= 50, les 10 meilleures forment la shortlist.
"""

SEUIL_RETENU = 50
PLAFOND_TOP = 10

NIVEAUX_DIPLOME = {"bac": 0, "bac+2": 2, "bac+3": 3, "bac+5": 5, "doctorat": 8}


def _diplome_suffisant(candidat, requis):
    if not requis:
        return True
    a = NIVEAUX_DIPLOME.get((candidat or "").lower(), -1)
    b = NIVEAUX_DIPLOME.get(requis.lower(), 0)
    return a >= b


def calculer_score(profil, offre):
    """Compare un profil extrait du CV à une offre.

    profil : dict {skills: [str], experience_years: int, degree: str}
    Retourne (score, details) — details sert a l'explicabilite cote interface.
    """
    requises = [s.lower() for s in (offre.required_skills or [])]
    possedees = [s.lower() for s in profil.get("skills", [])]

    trouvees = [s for s in requises if s in possedees]
    manquantes = [s for s in requises if s not in possedees]

    experience = profil.get("experience_years", 0) or 0
    diplome = profil.get("degree")

    # 1. Criteres eliminatoires : tout rejet est trace avec son motif exact.
    eliminatoires = []
    if offre.min_experience_years and experience < offre.min_experience_years:
        eliminatoires.append(
            f"Expérience {experience} an(s) < {offre.min_experience_years} an(s) requis"
        )
    if offre.min_degree and not _diplome_suffisant(diplome, offre.min_degree):
        eliminatoires.append(
            f"Diplôme {diplome or 'non renseigné'} < {offre.min_degree} requis"
        )

    # 2. Composantes du score
    part_competences = (len(trouvees) / len(requises) * 70) if requises else 70
    if offre.min_experience_years:
        ratio = min(experience / offre.min_experience_years, 1.5) / 1.5
    else:
        ratio = 1.0
    part_experience = ratio * 20
    part_diplome = 10 if _diplome_suffisant(diplome, offre.min_degree) else 0

    score = round(part_competences + part_experience + part_diplome)
    if eliminatoires:
        score = min(score, 45)  # ecarte par regle metier
    score = max(0, min(100, score))

    details = {
        "competences_trouvees": trouvees,
        "competences_manquantes": manquantes,
        "eliminatoires": eliminatoires,
        "composantes": [
            {
                "libelle": "Correspondance des compétences",
                "valeur": round(part_competences),
                "max": 70,
            },
            {"libelle": "Années d'expérience", "valeur": round(part_experience), "max": 20},
            {"libelle": "Niveau de diplôme", "valeur": part_diplome, "max": 10},
        ],
        "version_moteur": "regles-1.0",
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
