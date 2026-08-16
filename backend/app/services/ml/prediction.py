"""Usage du modèle appris lors de l'analyse d'une candidature.

Le modèle répond à une seule question : **ce profil convient-il à cette
offre ?** Il renvoie une probabilité, jamais une décision. Le moteur de
règles reste souverain : c'est lui qui écarte une candidature pour un motif
explicite, et l'avis du modèle ne peut ni annuler ni contourner un critère
éliminatoire.

Trois précautions gouvernent ce module :

  * **le même code de vectorisation qu'à l'entraînement** — le modèle voit
    exactement les mêmes caractéristiques, dans le même ordre, sous peine de
    recevoir des colonnes décalées ;
  * **l'ordre des caractéristiques est vérifié au chargement** — si le
    fichier a été produit par une version antérieure du vectoriseur, il est
    refusé plutôt qu'exploité de travers ;
  * **toute défaillance est silencieuse** — modèle absent, illisible ou
    incompatible, la fonction renvoie `None` et la plateforme calcule le
    score sans cette composante. Aucune analyse n'échoue faute de modèle.
"""
import logging
import os
import threading
from pathlib import Path

from . import caracteristiques

logger = logging.getLogger(__name__)

CHEMIN_MODELE = Path(
    os.environ.get(
        "CHEMIN_MODELE",
        Path(__file__).resolve().parents[3] / "models" / "correspondance.joblib",
    )
)

_verrou = threading.Lock()
_charge = False
_paquet = None


# --------------------------------------------------------------------------
# Chargement
# --------------------------------------------------------------------------

def _charger():
    """Charge le modèle une seule fois, sans jamais interrompre l'appelant."""
    global _charge, _paquet

    if _charge:
        return _paquet

    with _verrou:
        if _charge:
            return _paquet
        _charge = True

        if not CHEMIN_MODELE.exists():
            logger.info(
                "Aucun modèle appris en %s : le score sera calculé sans cette "
                "composante.", CHEMIN_MODELE,
            )
            return None

        try:
            import joblib

            paquet = joblib.load(CHEMIN_MODELE)
        except Exception as erreur:      # fichier corrompu, dependance absente
            logger.warning("Modèle illisible (%s) : composante ignorée.", erreur)
            return None

        # Un modele entraine sur d'autres caracteristiques produirait des
        # predictions arbitraires : mieux vaut s'en passer que s'y fier.
        attendues = paquet.get("caracteristiques")
        if attendues != caracteristiques.NOMS:
            logger.warning(
                "Le modèle a été entraîné sur un autre jeu de caractéristiques "
                "(%s au lieu de %s) : composante ignorée. Relancez "
                "l'entraînement.",
                len(attendues or []), len(caracteristiques.NOMS),
            )
            return None

        if paquet.get("classe_positive") not in (paquet.get("classes") or []):
            logger.warning("Classes du modèle incohérentes : composante ignorée.")
            return None

        _paquet = paquet
        logger.info(
            "Modèle « %s » chargé (protocole %s, exactitude %s).",
            paquet.get("version"),
            paquet.get("protocole_reference"),
            (paquet.get("evaluation") or {}).get("exactitude"),
        )
        return _paquet


def disponible():
    """Indique si un modèle exploitable est chargé."""
    return _charger() is not None


def informations():
    """Métadonnées du modèle, pour l'affichage et la documentation."""
    paquet = _charger()
    if not paquet:
        return None
    return {
        "version": paquet.get("version"),
        "protocole": paquet.get("protocole_reference"),
        "evaluation": paquet.get("evaluation"),
        "nb_caracteristiques": len(paquet.get("caracteristiques") or []),
    }


def recharger():
    """Oublie le modèle en mémoire ; le prochain appel le relira du disque."""
    global _charge, _paquet
    with _verrou:
        _charge = False
        _paquet = None


# --------------------------------------------------------------------------
# Prédiction
# --------------------------------------------------------------------------

def exigences_depuis_offre(offre):
    """Traduit une offre structurée dans la forme attendue par le vectoriseur.

    À l'entraînement, les exigences sont déduites d'annonces rédigées en texte
    libre. Sur la plateforme, elles sont saisies dans des champs dédiés : on
    les reprend telles quelles, plus fiables qu'une extraction.
    """
    competences = list(offre.required_skills or []) + list(
        getattr(offre, "preferred_skills", None) or []
    )
    return {
        "competences": set(competences),
        "experience": offre.min_experience_years or 0,
        "diplome": offre.min_degree,
        "intitule": offre.title or "",
    }


def probabilite(texte_cv, texte_offre, profil_ats=None, offre=None):
    """Probabilité que le profil convienne à l'offre, dans [0, 1].

    Renvoie `None` lorsque le modèle est indisponible ou que la prédiction
    échoue — l'analyse se poursuit alors sans cette composante.
    """
    paquet = _charger()
    if not paquet or not texte_cv:
        return None

    try:
        exigences = exigences_depuis_offre(offre) if offre is not None else None
        vecteur = caracteristiques.construire(
            texte_cv, texte_offre, profil_ats=profil_ats, exigences=exigences
        ).reshape(1, -1)

        modele = paquet["modele"]
        indice = list(modele.classes_).index(paquet["classe_positive"])
        return float(modele.predict_proba(vecteur)[0][indice])
    except Exception as erreur:
        logger.warning("Prédiction impossible (%s) : composante ignorée.", erreur)
        return None
