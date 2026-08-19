"""Similarité sémantique entre un CV et une offre (S3-05).

Deux niveaux, du plus fin au plus léger :

  1. Modèle de plongements lexicaux multilingue (Sentence Transformers).
     Il capture le SENS : « conception d'applications web » et « développeur
     web » se ressemblent fortement, bien qu'aucun mot ne soit commun.

  2. Repli sur une pondération TF-IDF avec similarité cosinus, lorsque le
     modèle n'est pas disponible. Moins fin, mais robuste et sans
     dépendance lourde — le service reste opérationnel en toutes
     circonstances.

Le modèle est chargé une seule fois puis conservé en mémoire ; les
plongements sont mis en cache, car le texte d'une offre est comparé à de
nombreux CV successifs.

Ce module est également destiné à alimenter la recherche documentaire du
chatbot au Sprint 4 : la fonction `encoder` y sera réutilisée telle quelle.
"""
import hashlib
import logging
import math
import re
from collections import Counter

logger = logging.getLogger(__name__)

# Modele multilingue compact : bon compromis qualite / poids pour le francais
NOM_MODELE = "paraphrase-multilingual-MiniLM-L12-v2"

_modele = None
_modele_charge = False
_cache_plongements = {}


def _charger_modele():
    global _modele, _modele_charge
    if _modele_charge:
        return _modele
    _modele_charge = True
    try:
        from sentence_transformers import SentenceTransformer
        _modele = SentenceTransformer(NOM_MODELE)
        logger.info("Modèle sémantique chargé : %s", NOM_MODELE)
    except Exception as exc:
        logger.warning("Modèle sémantique indisponible (%s) : repli TF-IDF.", exc)
        _modele = None
    return _modele


def _cle(texte):
    """Clé de cache, et rien d'autre.

    MD5 est ici choisi pour sa rapidité, non pour une propriété de sécurité :
    il s'agit d'indexer un texte déjà encodé, pas de protéger un secret.
    `usedforsecurity=False` le dit à l'analyseur statique comme au lecteur, et
    reste valide sur les systèmes où les algorithmes affaiblis sont désactivés.
    """
    return hashlib.md5(texte.encode("utf-8"), usedforsecurity=False).hexdigest()


def encoder(texte):
    """Renvoie le plongement d'un texte, ou None si le modèle est absent."""
    modele = _charger_modele()
    if modele is None or not texte:
        return None

    cle = _cle(texte)
    if cle in _cache_plongements:
        return _cache_plongements[cle]

    vecteur = modele.encode(texte[:5000], normalize_embeddings=True)
    _memoriser(cle, vecteur)
    return vecteur


def _memoriser(cle, vecteur):
    # Le cache est borne pour ne pas croitre indefiniment en production
    if len(_cache_plongements) > 500:
        _cache_plongements.clear()
    _cache_plongements[cle] = vecteur


def encoder_lot(textes):
    """Encode plusieurs textes en une passe.

    Un modèle de plongements traite un lot en une seule propagation avant :
    encoder cinquante documents d'un coup coûte nettement moins que cinquante
    appels successifs, où le temps se perd en préparation et en surcoût
    d'appel plutôt qu'en calcul. C'est ce qui rend la reconstruction de
    l'index de l'assistant supportable quand la base grandit.

    Les textes déjà connus sont repris du cache et ne sont pas réencodés.
    """
    modele = _charger_modele()
    if modele is None:
        return [None] * len(textes)

    resultats = [None] * len(textes)
    a_calculer, positions = [], []

    for i, texte in enumerate(textes):
        if not texte:
            continue
        cle = _cle(texte)
        if cle in _cache_plongements:
            resultats[i] = _cache_plongements[cle]
        else:
            a_calculer.append(texte[:5000])
            positions.append((i, cle))

    if a_calculer:
        try:
            vecteurs = modele.encode(
                a_calculer, normalize_embeddings=True, batch_size=32
            )
        except Exception as exc:
            # Un modele exotique pourrait ne pas accepter les lots : le repli
            # unitaire garantit que la fonctionnalite ne disparait pas.
            logger.warning("Encodage par lot indisponible (%s) : repli unitaire.", exc)
            for (i, _), texte in zip(positions, a_calculer):
                resultats[i] = encoder(texte)
            return resultats

        for (i, cle), vecteur in zip(positions, vecteurs):
            resultats[i] = vecteur
            _memoriser(cle, vecteur)

    return resultats


# ----------------------- Repli TF-IDF -----------------------

MOTS_OUTILS = {
    "le", "la", "les", "de", "des", "du", "un", "une", "et", "en", "pour", "avec",
    "sur", "dans", "au", "aux", "par", "ce", "cette", "ces", "est", "sont", "a",
    "the", "of", "and", "to", "in", "for", "with", "on", "at", "is", "are",
}


def _tokeniser(texte):
    mots = re.findall(r"[a-zà-ÿ0-9+#.]{2,}", (texte or "").lower())
    return [m for m in mots if m not in MOTS_OUTILS]


def _similarite_tfidf(texte_a, texte_b):
    """Cosinus sur des sacs de mots à pondération logarithmique.

    La fréquence est atténuée par un logarithme afin qu'un terme répété
    vingt fois ne domine pas la comparaison. Aucune pondération inverse
    n'est appliquée : sur deux documents seulement, elle pénaliserait
    justement les termes partagés, c'est-à-dire ceux qui portent la
    ressemblance.
    """
    ta, tb = _tokeniser(texte_a), _tokeniser(texte_b)
    if not ta or not tb:
        return 0.0

    ca, cb = Counter(ta), Counter(tb)

    def poids(compteur, mot):
        n = compteur.get(mot, 0)
        return 1 + math.log(n) if n else 0.0

    vocabulaire = set(ca) | set(cb)
    produit = sum(poids(ca, m) * poids(cb, m) for m in vocabulaire)
    norme_a = math.sqrt(sum(poids(ca, m) ** 2 for m in ca))
    norme_b = math.sqrt(sum(poids(cb, m) ** 2 for m in cb))
    if not norme_a or not norme_b:
        return 0.0
    return produit / (norme_a * norme_b)


# ----------------------- Interface publique -----------------------

def similarite(texte_cv, texte_offre):
    """Proximité entre deux textes, dans l'intervalle [0, 1].

    Renvoie également la méthode employée, afin que l'interface puisse
    indiquer au recruteur sur quelle base le rapprochement a été calculé.
    """
    if not texte_cv or not texte_offre:
        return 0.0, "indisponible"

    vec_cv = encoder(texte_cv)
    vec_offre = encoder(texte_offre)

    if vec_cv is not None and vec_offre is not None:
        # Vecteurs normalises : le produit scalaire est le cosinus
        score = float((vec_cv * vec_offre).sum())
        # Les plongements produisent rarement des valeurs negatives ici,
        # mais on borne par securite.
        return max(0.0, min(1.0, score)), "plongements"

    return _similarite_tfidf(texte_cv, texte_offre), "tf-idf"


def texte_offre(offre):
    """Assemble la description textuelle d'une offre pour la comparaison."""
    parties = [offre.title or "", offre.description or ""]
    if offre.required_skills:
        parties.append(" ".join(offre.required_skills))
    if offre.min_degree:
        parties.append(offre.min_degree)
    return "\n".join(parties)
