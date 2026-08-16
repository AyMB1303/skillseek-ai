"""Analyse linguistique du CV et extraction du profil structuré (S3-02).

Le pipeline combine deux approches complémentaires :
  * spaCy pour la normalisation linguistique (tokenisation, lemmatisation,
    suppression des mots outils) — indispensable pour comparer des formes
    fléchies (« développé », « développement ») à un référentiel ;
  * des motifs et un référentiel métier pour l'extraction structurée des
    compétences, du niveau de diplôme et des années d'expérience.

spaCy est chargé paresseusement et le module reste fonctionnel sans lui
(mode dégradé), ce qui évite d'imposer un modèle de langue aux tests.
"""
import logging
import re
import unicodedata
from datetime import date

from .competences import VARIANTES_TRIEES, INDEX_VARIANTES

logger = logging.getLogger(__name__)

_nlp = None
_nlp_charge = False


def _charger_spacy():
    """Charge le modèle français une seule fois pour tout le processus."""
    global _nlp, _nlp_charge
    if _nlp_charge:
        return _nlp
    _nlp_charge = True
    try:
        import spacy
        try:
            _nlp = spacy.load("fr_core_news_sm", disable=["ner", "parser"])
        except OSError:
            logger.warning("Modèle spaCy 'fr_core_news_sm' absent : mode dégradé.")
            _nlp = None
    except ImportError:
        logger.warning("spaCy absent : mode dégradé (normalisation simple).")
        _nlp = None
    return _nlp


def sans_accents(texte):
    """Supprime les accents : les CV les omettent fréquemment."""
    nfkd = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normaliser(texte):
    """Prépare le texte pour la recherche de compétences.

    Avec spaCy : lemmatisation et retrait des mots outils.
    Sans spaCy : minuscules et suppression des accents.
    """
    base = sans_accents((texte or "").lower())
    nlp = _charger_spacy()
    if nlp is None:
        return base

    # On limite la taille traitee : un CV depasse rarement 30 000 caracteres
    doc = nlp(base[:30000])
    lemmes = [t.lemma_ for t in doc if not t.is_stop and not t.is_punct and not t.is_space]
    # On conserve le texte brut ET les lemmes : certaines competences sont
    # des sigles que la lemmatisation ne doit pas masquer.
    return base + " " + " ".join(lemmes)


# ----------------------- Compétences -----------------------

def extraire_competences(texte):
    """Repère les compétences du référentiel présentes dans le texte."""
    normalise = normaliser(texte)
    trouvees = []

    for variante in VARIANTES_TRIEES:
        # Bornes de mot : evite que « r » corresponde a chaque lettre r
        motif = r"(?<![\w+#])" + re.escape(sans_accents(variante)) + r"(?![\w+#])"
        if re.search(motif, normalise):
            canonique = INDEX_VARIANTES[variante]
            if canonique not in trouvees:
                trouvees.append(canonique)

    return trouvees


# ----------------------- Diplôme -----------------------

MOTIFS_DIPLOME = [
    (r"\b(doctorat|phd|these de doctorat)\b", "Doctorat"),
    (r"\b(bac\s*\+\s*5|master|ingenieur|mastere|msc|mba)\b", "Bac+5"),
    (r"\b(bac\s*\+\s*3|licence|bachelor|bsc)\b", "Bac+3"),
    (r"\b(bac\s*\+\s*2|dut|bts|deug)\b", "Bac+2"),
    (r"\b(baccalaureat|bac)\b", "Bac"),
]

ORDRE_DIPLOME = ["Bac", "Bac+2", "Bac+3", "Bac+5", "Doctorat"]


def extraire_diplome(texte):
    """Renvoie le niveau de diplôme le plus élevé mentionné."""
    normalise = sans_accents((texte or "").lower())
    trouves = [
        niveau for motif, niveau in MOTIFS_DIPLOME if re.search(motif, normalise)
    ]
    if not trouves:
        return None
    return max(trouves, key=ORDRE_DIPLOME.index)


# ----------------------- Expérience -----------------------

# « 5 ans d'experience », « experience : 3 ans », « 7+ years »
MOTIFS_EXPERIENCE = [
    r"(\d{1,2})\s*\+?\s*(?:ans?|annees?|years?)\s*(?:d[e']\s*)?(?:experience|exp)",
    r"experience\s*(?:professionnelle)?\s*[:\-]?\s*(\d{1,2})\s*\+?\s*(?:ans?|annees?)",
]

# Periodes datees : « 2019 - 2023 », « 2020 – present »
MOTIF_PERIODE = r"(19[89]\d|20[0-4]\d)\s*[-–—/]\s*(19[89]\d|20[0-4]\d|present|aujourd'hui|actuel)"


def extraire_experience(texte):
    """Estime les années d'expérience.

    Deux sources, la mention explicite primant sur le calcul par périodes :
    une durée annoncée par le candidat est plus fiable que la somme de dates
    qui peuvent se chevaucher (formations et emplois simultanés).
    """
    normalise = sans_accents((texte or "").lower())

    # 1. Mention explicite
    valeurs = []
    for motif in MOTIFS_EXPERIENCE:
        valeurs += [int(m) for m in re.findall(motif, normalise)]
    if valeurs:
        return min(max(valeurs), 45)  # borne haute de bon sens

    # 2. Calcul a partir des periodes datees (union, sans double comptage)
    annee_courante = date.today().year
    intervalles = []
    for debut, fin in re.findall(MOTIF_PERIODE, normalise):
        d = int(debut)
        f = annee_courante if not fin.isdigit() else int(fin)
        if f >= d and f - d <= 45:
            intervalles.append((d, f))

    if not intervalles:
        return 0

    intervalles.sort()
    total, courant_debut, courant_fin = 0, *intervalles[0]
    for d, f in intervalles[1:]:
        if d <= courant_fin:                 # chevauchement : on fusionne
            courant_fin = max(courant_fin, f)
        else:
            total += courant_fin - courant_debut
            courant_debut, courant_fin = d, f
    total += courant_fin - courant_debut
    return min(total, 45)


# Le profil complet n'est plus assemble ici : `services/ats.py` produit un
# profil structure bien plus riche (experiences datees, langues, sections) a
# partir du meme texte. Les fonctions ci-dessus restent utilisees comme briques
# de repli lorsque l'analyse structurelle echoue.
