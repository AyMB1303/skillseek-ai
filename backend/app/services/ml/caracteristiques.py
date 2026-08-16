"""Transformation d'une paire (CV, offre) en vecteur de caractéristiques.

Le modèle ne reçoit pas les textes bruts mais un ensemble de signaux
comparables d'une paire à l'autre. Deux familles s'y combinent :

  * les **signaux sémantiques**, issus des plongements multilingues — c'est
    eux qui permettent au modèle appris sur des documents anglais de
    fonctionner sur des documents français, la représentation vectorielle
    étant indépendante de la langue ;

  * les **signaux d'adéquation**, calculés par le parseur existant : part des
    exigences satisfaites, écart d'expérience, écart de diplôme. Ils
    apportent une information que la proximité de sens ne capture pas — un
    CV peut ressembler à une offre tout en manquant la compétence
    indispensable.

Principe de conception : toutes les caractéristiques sont **relationnelles**.
Elles décrivent le rapport entre un profil et une exigence, jamais une
propriété absolue du document. Les longueurs de texte, par exemple, ont été
écartées : elles identifiaient l'offre plutôt que de mesurer l'adéquation, et
le modèle s'en servait comme raccourci au lieu d'apprendre à juger.

Le même code sert à l'entraînement et à la prédiction : c'est la condition
pour que le modèle voie exactement la même chose dans les deux situations.
"""
import re

import numpy as np

from .. import ats, semantique
from ..competences import canoniser
from ..scoring import NIVEAUX_DIPLOME

# L'ordre doit rester stable entre l'entrainement et la prediction, sous peine
# de nourrir le modele avec des colonnes decalees.
NOMS = [
    # Proximite de sens
    "similarite_globale",
    "similarite_competences",
    "similarite_intitules",
    # Adequation des competences
    "part_exigences_satisfaites",
    "jaccard_competences",
    "nb_competences_communes",
    "nb_exigences_manquantes",
    "couverture_du_profil",
    # Adequation de l'experience
    "ratio_experience",
    "ecart_experience",
    "experience_suffisante",
    # Adequation du diplome
    "ecart_diplome",
    "diplome_suffisant",
    # Richesse du profil, independante de l'offre
    "nb_competences_cv",
    "nb_postes",
    "nb_certifications",
    "nb_langues",
]


def _niveau_diplome(libelle):
    return NIVEAUX_DIPLOME.get((libelle or "").lower(), -1)


MOTIFS_EXPERIENCE = [
    r"(\d{1,2})\s*\+?\s*(?:ans?|annees?|years?)\s*(?:of\s*)?(?:d[e']\s*)?experience",
    r"experience\s*[:\-]?\s*(\d{1,2})\s*\+?\s*(?:ans?|years?)",
    r"minimum\s*(?:of\s*)?(\d{1,2})\s*(?:ans?|years?)",
    r"at least\s*(\d{1,2})\s*years?",
]


def _experience_mentionnee(texte):
    """Repère « 5+ years of experience » et ses variantes françaises."""
    normalise = ats.sans_accents((texte or "").lower())
    valeurs = []
    for motif in MOTIFS_EXPERIENCE:
        valeurs += [int(v) for v in re.findall(motif, normalise)]
    return min(max(valeurs), 30) if valeurs else 0


def _intitules_profil(profil):
    """Intitulés des postes occupés, support de la comparaison de métier."""
    titres = [p.get("position") for p in (profil.get("work") or []) if p.get("position")]
    return " ".join(titres[:4])


def _intitule_offre(texte_offre):
    """Première ligne substantielle d'une annonce : son intitulé de poste."""
    for ligne in (texte_offre or "").splitlines():
        nettoyee = ligne.strip()
        if 8 <= len(nettoyee) <= 120:
            return nettoyee
    return (texte_offre or "")[:120]


def extraire_exigences(texte_offre):
    """Déduit les exigences d'une offre rédigée en texte libre.

    Les annonces du corpus n'ont pas de champs structurés : compétences,
    expérience et diplôme doivent en être extraits par les mêmes moyens que
    pour un CV.
    """
    return {
        "competences": set(ats.extraire_competences(texte_offre)),
        "experience": _experience_mentionnee(texte_offre),
        "diplome": ats.diplome_le_plus_eleve([], texte_offre),
        "intitule": _intitule_offre(texte_offre),
    }


def construire(texte_cv, texte_offre, profil_ats=None, exigences=None):
    """Produit le vecteur de caractéristiques d'une paire (CV, offre)."""
    profil = profil_ats or ats.analyser_cv(texte_cv)
    besoin = exigences or extraire_exigences(texte_offre)

    competences_cv = {canoniser(c) for c in profil.get("skills", [])}
    competences_offre = {canoniser(c) for c in besoin.get("competences", set())}
    communes = competences_cv & competences_offre
    union = competences_cv | competences_offre

    # --- Proximite de sens ---
    similarite, _ = semantique.similarite(texte_cv, texte_offre)

    texte_comp_cv = " ".join(sorted(competences_cv)) or "aucune"
    texte_comp_offre = " ".join(sorted(competences_offre)) or "aucune"
    similarite_comp, _ = semantique.similarite(texte_comp_cv, texte_comp_offre)

    # Comparaison des metiers exerces avec l'intitule du poste : un candidat
    # peut partager du vocabulaire sans avoir jamais occupe ce type de poste.
    similarite_titres, _ = semantique.similarite(
        _intitules_profil(profil) or "aucun poste", besoin.get("intitule") or "poste"
    )

    # --- Adequation ---
    experience_cv = profil.get("totalExperienceYears", 0) or 0
    experience_offre = besoin.get("experience", 0) or 0
    diplome_cv = _niveau_diplome(profil.get("highestDegree"))
    diplome_offre = _niveau_diplome(besoin.get("diplome"))

    ratio_experience = (
        min(experience_cv / experience_offre, 3.0) if experience_offre else 1.0
    )

    return np.array([
        similarite,
        similarite_comp,
        similarite_titres,
        len(communes) / len(competences_offre) if competences_offre else 0.0,
        len(communes) / len(union) if union else 0.0,
        len(communes),
        len(competences_offre - competences_cv),
        # Part des competences du candidat qui interessent l'offre : distingue
        # un profil cible d'un profil generaliste qui coche par accident.
        len(communes) / len(competences_cv) if competences_cv else 0.0,
        ratio_experience,
        experience_cv - experience_offre,
        1.0 if experience_cv >= experience_offre else 0.0,
        diplome_cv - diplome_offre,
        1.0 if diplome_cv >= diplome_offre else 0.0,
        len(competences_cv),
        len(profil.get("work") or []),
        len(profil.get("certificates") or []),
        len(profil.get("languages") or []),
    ], dtype=np.float32)


def construire_lot(paires, journal=None):
    """Vectorise une liste de paires (texte_cv, texte_offre).

    Le profil ATS de chaque CV et les exigences de chaque offre sont mis en
    cache : le corpus recombine un nombre restreint de documents, et leur
    analyse est l'opération la plus coûteuse du traitement.
    """
    cache_profils = {}
    cache_exigences = {}
    vecteurs = []

    for index, (cv, offre) in enumerate(paires):
        if cv not in cache_profils:
            cache_profils[cv] = ats.analyser_cv(cv)
        if offre not in cache_exigences:
            cache_exigences[offre] = extraire_exigences(offre)

        vecteurs.append(
            construire(cv, offre, cache_profils[cv], cache_exigences[offre])
        )

        if journal and (index + 1) % 500 == 0:
            journal(f"  {index + 1}/{len(paires)} paires traitées")

    return np.vstack(vecteurs)
