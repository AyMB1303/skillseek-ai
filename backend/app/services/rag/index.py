"""Index vectoriel : encodage des documents et recherche par similarité.

Le principe de la récupération augmentée repose sur une idée simple : plutôt
que de chercher les mots de la question dans les documents, on compare le
*sens* de la question au sens de chaque document. Deux formulations
différentes d'une même intention se retrouvent alors proches l'une de
l'autre dans l'espace vectoriel.

L'index est conservé en mémoire et reconstruit uniquement lorsque les
données sous-jacentes ont changé.
"""
import logging
import math
import re
from collections import Counter

from .. import semantique
from . import administration, connaissance

logger = logging.getLogger(__name__)

# Index par domaine et portee : {(domaine, portee): (empreinte, docs, vecteurs)}
#
# Le domaine separe deux bases de connaissance distinctes. « recrutement »
# porte les offres et les candidatures, « administration » les comptes, les
# droits et les signalements. Cette separation n'est pas cosmetique : le role
# administrateur ne detient pas `view_applications`, et un index unique lui
# donnerait par la conversation ce que le modele de droits lui refuse.
_index = {}

MOTS_OUTILS = {
    "le", "la", "les", "de", "des", "du", "un", "une", "et", "en", "pour", "avec",
    "sur", "dans", "au", "aux", "par", "ce", "cette", "ces", "est", "sont", "a",
    "qui", "que", "quoi", "quel", "quelle", "quels", "quelles", "combien", "je",
    "tu", "il", "elle", "nous", "vous", "ils", "elles", "me", "moi", "mon", "ma",
    "mes", "son", "sa", "ses", "leur", "leurs", "plus", "moins", "tout", "tous",
}


def _tokeniser(texte):
    mots = re.findall(r"[a-zà-ÿ0-9+#.]{2,}", (texte or "").lower())
    return [m for m in mots if m not in MOTS_OUTILS]


def _similarite_lexicale(question, texte):
    """Repli lorsque le modèle de plongements n'est pas disponible."""
    a, b = Counter(_tokeniser(question)), Counter(_tokeniser(texte))
    if not a or not b:
        return 0.0

    def poids(compteur, mot):
        n = compteur.get(mot, 0)
        return 1 + math.log(n) if n else 0.0

    vocabulaire = set(a) | set(b)
    produit = sum(poids(a, m) * poids(b, m) for m in vocabulaire)
    na = math.sqrt(sum(poids(a, m) ** 2 for m in a))
    nb = math.sqrt(sum(poids(b, m) ** 2 for m in b))
    return produit / (na * nb) if na and nb else 0.0


def _construire(portee, domaine):
    documents = (
        administration.documents() if domaine == "administration"
        else connaissance.construire(portee)
    )
    # Le titre est repete : il porte l'essentiel du sens et gagne a peser
    # davantage que le corps du document dans la representation.
    #
    # L'encodage se fait en une seule passe. Reconstruire l'index document par
    # document etait la depense la plus lourde de l'assistant : chaque appel
    # payait la preparation du lot pour un seul texte.
    textes = [f"{doc.titre}. {doc.titre}. {doc.texte}" for doc in documents]
    return documents, semantique.encoder_lot(textes)


def obtenir(portee=None, domaine="recrutement"):
    """Renvoie l'index à jour pour le domaine et la portée demandés."""
    signature = (
        administration.empreinte() if domaine == "administration"
        else connaissance.empreinte(portee)
    )
    cle = (domaine, portee)
    cache = _index.get(cle)
    if cache and cache[0] == signature:
        return cache[1], cache[2]

    documents, vecteurs = _construire(portee, domaine)
    _index[cle] = (signature, documents, vecteurs)
    logger.info(
        "Index reconstruit : %d documents (domaine %s, portée %s)",
        len(documents), domaine, portee,
    )
    return documents, vecteurs


def invalider():
    """Force la reconstruction au prochain appel."""
    _index.clear()


def rechercher(question, portee=None, limite=6, seuil=0.15, domaine="recrutement"):
    """Retrouve les documents les plus proches de la question.

    Renvoie une liste de couples (document, score de proximité), triée par
    pertinence décroissante. Les documents trop éloignés sont écartés : mieux
    vaut répondre sur peu d'éléments pertinents que noyer le générateur dans
    du contexte hors sujet.
    """
    documents, vecteurs = obtenir(portee, domaine)
    if not documents:
        return []

    vecteur_question = semantique.encoder(question)
    resultats = []

    for doc, vecteur in zip(documents, vecteurs):
        if vecteur_question is not None and vecteur is not None:
            score = float((vecteur_question * vecteur).sum())
        else:
            score = _similarite_lexicale(question, f"{doc.titre} {doc.texte}")
        resultats.append((doc, max(0.0, min(1.0, score))))

    resultats.sort(key=lambda r: r[1], reverse=True)
    retenus = [(d, s) for d, s in resultats if s >= seuil][:limite]

    # Si rien n'atteint le seuil, on conserve les meilleurs resultats : une
    # reponse approximative accompagnee de ses sources vaut mieux qu'un refus.
    return retenus or resultats[:2]


_methode = None


def methode_active():
    """Indique si la recherche s'appuie sur les plongements ou sur le repli.

    La reponse est retenue : la disponibilite du modele ne change pas en cours
    d'execution, et l'interroger a chaque reponse revenait a encoder un texte
    pour rien.
    """
    global _methode
    if _methode is None:
        _methode = "plongements" if semantique.encoder("test") is not None else "lexicale"
    return _methode
