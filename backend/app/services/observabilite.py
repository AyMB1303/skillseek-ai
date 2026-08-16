"""Mesure et traçabilité du traitement d'une candidature.

Deux besoins distincts, servis par le même module.

**Mesurer.** Une analyse enchaîne six traitements de coûts très inégaux :
l'extraction lit un fichier, la reconnaissance optique fait tourner un moteur
externe, les plongements font passer un texte dans un réseau de neurones. Quand
une analyse prend huit secondes, savoir *laquelle* des six étapes les a
consommées change complètement ce qu'il faut corriger. Sans mesure, on optimise
au jugé.

**Tracer.** Un score n'est comparable dans le temps que si l'on sait avec quoi
il a été calculé. Le moteur de règles évolue, le modèle appris est réentraîné,
le modèle de plongements pourrait être remplacé. Consigner ces versions à côté
de la note permet de répondre à la seule question qui vaille lorsqu'un candidat
conteste : « qu'est-ce qui a produit ce chiffre, exactement ? ».

Les durées sont en millisecondes entières. La précision de la microseconde ne
veut rien dire ici — le même CV analysé deux fois varie de plusieurs dizaines
de millisecondes selon la charge de la machine.
"""
import logging
import os
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Version du moteur de regles. Elle vit ici plutot que dans `scoring` parce
# qu'elle sert desormais a deux choses : expliquer un score, et dater une
# analyse dans l'historique.
VERSION_MOTEUR = "ats-4.0"


class Chronometre:
    """Accumule la durée de chaque étape d'un traitement.

    Utilisé comme gestionnaire de contexte imbriqué :

        chrono = Chronometre()
        with chrono.etape("extraction"):
            ...

    Une étape qui lève une exception est tout de même mesurée puis marquée en
    échec : c'est précisément l'étape lente qui casse qu'on cherche à voir.
    """

    def __init__(self):
        self.durees = {}
        self.echecs = set()
        self._debut = time.perf_counter()

    @contextmanager
    def etape(self, nom):
        depart = time.perf_counter()
        try:
            yield
        except Exception:
            self.echecs.add(nom)
            raise
        finally:
            self.durees[nom] = round((time.perf_counter() - depart) * 1000)

    @property
    def total(self):
        return round((time.perf_counter() - self._debut) * 1000)

    def resultat(self):
        """Mesures prêtes à être jointes au détail d'une analyse."""
        return {
            "etapes_ms": dict(self.durees),
            "total_ms": self.total,
            # L'etape la plus couteuse est calculee ici plutot que dans
            # l'interface : c'est une lecture des donnees, pas une mise en forme.
            "etape_la_plus_longue": (
                max(self.durees, key=self.durees.get) if self.durees else None
            ),
            "etapes_en_echec": sorted(self.echecs),
        }

    def journaliser(self, contexte=""):
        detail = " ".join(f"{nom}={ms}ms" for nom, ms in self.durees.items())
        logger.info("Analyse %s terminee en %dms — %s", contexte, self.total, detail)


def provenance(methode_similarite=None):
    """Identifie ce qui a produit le résultat : versions et modèles.

    `GIT_SHA` est injecté à la construction de l'image. En développement la
    variable est absente : on l'indique plutôt que d'inventer une valeur.
    """
    from .ml import prediction
    from .semantique import NOM_MODELE

    infos_modele = prediction.informations()

    return {
        "version_moteur": VERSION_MOTEUR,
        "modele_semantique": NOM_MODELE if methode_similarite == "plongements" else None,
        "methode_similarite": methode_similarite,
        "modele_appris": (infos_modele or {}).get("version"),
        "commit": os.getenv("GIT_SHA") or "developpement",
        "analyse_le": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
