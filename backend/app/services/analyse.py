"""Orchestration de l'analyse complète d'une candidature (S3-08).

Enchaîne les quatre étapes du traitement et produit un résultat unique,
directement exploitable par l'interface :

    CV (PDF)  →  extraction  →  analyse linguistique  →  profil structuré
                                        ↓
                      similarité sémantique avec l'offre
                                        ↓
                  moteur de règles + pondération  →  score expliqué

Chaque étape est traçable : le résultat indique la méthode d'extraction
employée, le profil retenu et le détail du calcul, de sorte qu'un recruteur
puisse toujours comprendre l'origine d'une note.
"""
import logging

from . import ats, extraction, semantique
from .scoring import calculer_score

logger = logging.getLogger(__name__)


def analyser_candidature(candidature, chemin_cv=None):
    """Analyse une candidature de bout en bout et met à jour son score.

    L'objet `candidature` est modifié en mémoire ; la validation en base
    reste à la charge de l'appelant, qui maîtrise la transaction.
    """
    offre = candidature.offer
    chemin = chemin_cv or candidature.cv_path

    # 1. Extraction du texte (couche native, puis OCR si necessaire)
    resultat = extraction.extraire_texte(chemin)

    if not resultat.reussie:
        candidature.score = None
        candidature.score_details = {
            "statut": "extraction_echouee",
            "message": (
                resultat.erreur
                or "Le contenu du CV n'a pas pu être lu automatiquement."
            ),
            "extraction": resultat.to_dict(),
            "action_suggeree": "Saisir le profil manuellement pour obtenir un score.",
        }
        return candidature.score_details

    # 2. Profil structure normalise (identite, experiences, formations,
    #    certifications, langues, competences)
    profil_ats = ats.analyser_cv(resultat.texte)
    profil = ats.vers_profil_scoring(profil_ats)

    # 3. Proximite semantique entre le CV et l'offre
    similarite, methode_sim = semantique.similarite(
        resultat.texte, semantique.texte_offre(offre)
    )

    # 4. Score hybride : regles metiers + ponderation des composantes
    score, details = calculer_score(profil, offre, similarite_semantique=similarite)

    details.update(
        {
            "statut": "analysee",
            "profil_analyse": profil,
            "profil_ats": profil_ats,
            "extraction": resultat.to_dict(),
            "similarite": {"valeur": round(similarite, 3), "methode": methode_sim},
        }
    )

    candidature.score = score
    candidature.score_details = details
    return details


def analyser_texte(texte, offre):
    """Analyse un texte de CV déjà extrait, sans passer par un fichier.

    Utilisé par les tests et par les scripts d'évaluation du modèle.
    """
    profil_ats = ats.analyser_cv(texte)
    profil = ats.vers_profil_scoring(profil_ats)
    similarite, methode = semantique.similarite(texte, semantique.texte_offre(offre))
    score, details = calculer_score(profil, offre, similarite_semantique=similarite)
    details.update(
        {
            "statut": "analysee",
            "profil_analyse": profil,
            "profil_ats": profil_ats,
            "similarite": {"valeur": round(similarite, 3), "methode": methode},
        }
    )
    return score, details
