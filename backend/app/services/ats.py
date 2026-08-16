"""Analyse syntaxique d'un CV selon les conventions ATS (S3-02b).

Un système de suivi des candidatures (ATS) ne se contente pas de relever
des mots-clés : il reconstruit un profil structuré et normalisé, dont le
schéma est directement inspiré de JSON Resume, format d'échange de fait
dans l'industrie du recrutement.

Le traitement se déroule en trois temps :

  1. Découpage du document en sections (identité, expérience, formation,
     compétences, certifications, langues). Cette étape conditionne la
     qualité de tout le reste : une date lue dans la section « formation »
     ne doit pas alimenter le calcul de l'expérience professionnelle.
  2. Extraction propre à chaque section.
  3. Consolidation : durée totale d'expérience, niveau de diplôme le plus
     élevé, compétences canoniques.
"""
import re
import unicodedata
from datetime import date

from .competences import INDEX_VARIANTES, VARIANTES_TRIEES

# --------------------------------------------------------------------------
# Découpage en sections
# --------------------------------------------------------------------------

# Intitules rencontres dans les CV francais et anglais, par section normalisee
EN_TETES = {
    "experience": [
        "experiences professionnelles", "experience professionnelle", "experiences",
        "experience", "parcours professionnel", "parcours", "emplois", "carriere",
        "work experience", "professional experience", "employment history", "work history",
    ],
    "formation": [
        "formation", "formations", "education", "diplomes", "diplome", "cursus",
        "parcours academique", "etudes", "academic background", "qualifications",
    ],
    "competences": [
        "competences", "competence", "competences techniques", "skills",
        "technical skills", "savoir-faire", "expertise", "technologies",
    ],
    "certifications": [
        "certifications", "certification", "certificats", "certificates",
        "accreditations", "licences",
    ],
    "langues": ["langues", "langue", "languages", "language skills"],
    "projets": ["projets", "projet", "projects", "realisations"],
    "interets": ["centres d'interet", "interets", "loisirs", "hobbies", "interests"],
}


def sans_accents(texte):
    """Retire les accents : les CV les omettent fréquemment.

    Exposée publiquement car les autres modules d'analyse s'appuient sur la
    même normalisation, condition pour que leurs comparaisons concordent.
    """
    nfkd = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# Conserve pour les appels internes existants
_sans_accents = sans_accents


def _identifier_section(ligne):
    """Renvoie la section correspondante si la ligne est un en-tête, sinon None."""
    brute = ligne.strip()
    if not brute or len(brute) > 60:
        return None

    # Un en-tete ne se termine pas par une ponctuation de phrase
    nettoyee = _sans_accents(brute.lower()).strip(" :–—-•\t")
    nettoyee = re.sub(r"[^a-z' ]", "", nettoyee).strip()
    if not nettoyee:
        return None

    for section, intitules in EN_TETES.items():
        if nettoyee in intitules:
            return section
    return None


def decouper_en_sections(texte):
    """Répartit les lignes du CV par section.

    Tout ce qui précède le premier en-tête est classé en « entete »,
    zone où se trouvent habituellement le nom et les coordonnées.
    """
    sections = {"entete": []}
    courante = "entete"

    for ligne in (texte or "").splitlines():
        detectee = _identifier_section(ligne)
        if detectee:
            courante = detectee
            sections.setdefault(courante, [])
            continue
        sections.setdefault(courante, []).append(ligne)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


# --------------------------------------------------------------------------
# Identité et coordonnées
# --------------------------------------------------------------------------

MOTIF_EMAIL = r"[\w.+-]+@[\w-]+\.[\w.-]+"
# Formats rencontres : +212 6 12 34 56 78, 06.12.34.56.78, (0) 612-345-678
MOTIF_TELEPHONE = r"(?:\+\d{1,3}[\s.-]?)?(?:\(?\d\)?[\s.-]?)?(?:\d[\s.-]?){8,13}\d"
MOTIF_LINKEDIN = r"(?:linkedin\.com/in/|linkedin\s*:\s*)([\w\-À-ÿ]+)"

# Une annee isolee ou une periode ne doit jamais etre prise pour un numero
MOTIF_ANNEE_SEULE = re.compile(r"^(?:19|20)\d{2}$")


def extraire_identite(texte, entete=""):
    """Coordonnées du candidat. Le nom est cherché dans l'en-tête du document."""
    email = re.search(MOTIF_EMAIL, texte or "")
    linkedin = re.search(MOTIF_LINKEDIN, (texte or "").lower())

    # Le telephone est cherche dans les premieres lignes du document, ou
    # figurent les coordonnees. On decoupe sur les separateurs courants afin
    # d'isoler le numero du reste de la ligne de contact.
    telephone = None
    for ligne in (texte or "").splitlines()[:20]:
        if telephone:
            break
        for fragment in re.split(r"[|•·]|\s{3,}", ligne):
            fragment = fragment.strip()
            if not fragment or "@" in fragment or MOTIF_ANNEE_SEULE.match(fragment):
                continue
            candidat = re.search(MOTIF_TELEPHONE, fragment)
            if not candidat:
                continue
            chiffres = re.sub(r"\D", "", candidat.group())
            # Un numero comporte 9 a 15 chiffres ; en dessous c'est une date.
            if 9 <= len(chiffres) <= 15:
                telephone = candidat.group().strip()
                break

    # Le nom : premiere ligne substantielle, sans chiffre ni arobase,
    # de deux a quatre mots, majoritairement capitalisee.
    nom = None
    for ligne in (entete or texte or "").splitlines()[:8]:
        candidat = ligne.strip(" -–—|•\t")
        if not candidat or "@" in candidat or re.search(r"\d", candidat):
            continue
        mots = candidat.split()
        if 2 <= len(mots) <= 4 and sum(m[:1].isupper() for m in mots) >= len(mots) - 1:
            nom = candidat
            break

    return {
        "name": nom,
        "email": email.group() if email else None,
        "phone": telephone,
        "linkedin": linkedin.group(1) if linkedin else None,
    }


# --------------------------------------------------------------------------
# Expériences professionnelles
# --------------------------------------------------------------------------

MOIS = (
    "janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre"
    "|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
)
EN_COURS = r"present|aujourd'hui|actuel|actuellement|current|now|ce jour"

# « 2019 - 2023 », « janvier 2019 – mars 2021 », « 09/2019 - 06/2022 »
MOTIF_PERIODE = re.compile(
    r"(?:(" + MOIS + r")\s+)?(?:(\d{1,2})[/.])?((?:19|20)\d{2})"
    r"\s*(?:[-–—]|a|à|to|jusqu'a)\s*"
    r"(?:(?:(" + MOIS + r")\s+)?(?:(\d{1,2})[/.])?((?:19|20)\d{2})|(" + EN_COURS + r"))",
    re.IGNORECASE,
)

# Separateurs frequents entre intitule de poste et employeur
SEPARATEURS_POSTE = r"\s+(?:chez|at|@|au sein de|-|–|—|\||,)\s+"

MOTS_POSTE = (
    "developpeur|developpeuse|ingenieur|ingenieure|consultant|consultante|analyste|"
    "chef de projet|responsable|directeur|directrice|technicien|technicienne|architecte|"
    "administrateur|administratrice|data scientist|data analyst|designer|stagiaire|"
    "manager|lead|expert|charge|chargee|assistant|assistante|engineer|developer|"
    "intern|specialist|officer|coordinateur|coordinatrice"
)


def _mois_vers_numero(nom_mois):
    if not nom_mois:
        return None
    ordre = MOIS.split("|")
    court = _sans_accents(nom_mois.lower())[:3]
    for i, m in enumerate(ordre[:12]):
        if _sans_accents(m)[:3] == court:
            return i + 1
    for i, m in enumerate(ordre[12:]):
        if m == court:
            return i + 1
    return None


def _analyser_periode(correspondance):
    """Convertit une correspondance de période en (début, fin, en_cours)."""
    g = correspondance.groups()
    mois_debut, _, annee_debut, mois_fin, _, annee_fin, mention_cours = g

    debut = (int(annee_debut), _mois_vers_numero(mois_debut) or 1)
    if mention_cours:
        aujourd_hui = date.today()
        return debut, (aujourd_hui.year, aujourd_hui.month), True
    if annee_fin:
        return debut, (int(annee_fin), _mois_vers_numero(mois_fin) or 12), False
    return debut, debut, False


def _duree_en_mois(debut, fin):
    return max(0, (fin[0] - debut[0]) * 12 + (fin[1] - debut[1]))


def extraire_experiences(section):
    """Reconstruit la liste des postes occupés.

    Chaque période datée ouvre une entrée ; les lignes qui la suivent, jusqu'à
    la période suivante, en constituent la description. L'intitulé et
    l'employeur sont recherchés dans cette même entrée.
    """
    if not section:
        return []

    lignes = [li for li in section.splitlines()]
    entrees = []
    courante = None

    for ligne in lignes:
        periode = MOTIF_PERIODE.search(_sans_accents(ligne.lower()))
        if periode:
            if courante:
                entrees.append(courante)
            debut, fin, en_cours = _analyser_periode(periode)
            courante = {
                "startDate": f"{debut[0]:04d}-{debut[1]:02d}",
                "endDate": None if en_cours else f"{fin[0]:04d}-{fin[1]:02d}",
                "current": en_cours,
                "months": _duree_en_mois(debut, fin),
                "position": None,
                "company": None,
                "summary": [],
                "_ligne_source": ligne,
            }
            # L'intitule figure souvent sur la meme ligne que la periode
            reste = MOTIF_PERIODE.sub("", ligne, count=1).strip(" :-–—|\t")
            if reste:
                courante["summary"].append(reste)
        elif courante is not None and ligne.strip():
            courante["summary"].append(ligne.strip())

    if courante:
        entrees.append(courante)

    # Identification de l'intitule et de l'employeur dans chaque entree
    for entree in entrees:
        for candidat in entree["summary"][:3]:
            nettoye = candidat.strip(" •-–—*\t")
            if re.search(MOTS_POSTE, _sans_accents(nettoye.lower())):
                morceaux = re.split(SEPARATEURS_POSTE, nettoye, maxsplit=1)
                entree["position"] = morceaux[0].strip()
                if len(morceaux) > 1:
                    entree["company"] = morceaux[1].strip()
                break
        entree["summary"] = " ".join(entree["summary"])[:400]
        entree.pop("_ligne_source", None)

    return entrees


def annees_experience(experiences):
    """Durée totale en années, sans compter deux fois les postes simultanés."""
    intervalles = []
    for e in experiences:
        if not e.get("startDate"):
            continue
        debut = tuple(int(x) for x in e["startDate"].split("-"))
        if e.get("current"):
            aujourd_hui = date.today()
            fin = (aujourd_hui.year, aujourd_hui.month)
        elif e.get("endDate"):
            fin = tuple(int(x) for x in e["endDate"].split("-"))
        else:
            continue
        intervalles.append((debut, fin))

    if not intervalles:
        return 0

    intervalles.sort()
    total, (cd, cf) = 0, intervalles[0]
    for debut, fin in intervalles[1:]:
        if debut <= cf:                      # chevauchement : fusion
            cf = max(cf, fin)
        else:
            total += _duree_en_mois(cd, cf)
            cd, cf = debut, fin
    total += _duree_en_mois(cd, cf)
    return min(round(total / 12), 45)


# --------------------------------------------------------------------------
# Formation
# --------------------------------------------------------------------------

NIVEAUX = [
    (r"\b(doctorat|phd|these de doctorat)\b", "Doctorat", 8),
    (r"\b(bac\s*\+\s*5|master|ingenieur|mastere|msc|mba|dess|dea)\b", "Bac+5", 5),
    (r"\b(bac\s*\+\s*3|licence|bachelor|bsc|maitrise)\b", "Bac+3", 3),
    (r"\b(bac\s*\+\s*2|dut|bts|deug|deust)\b", "Bac+2", 2),
    (r"\b(baccalaureat|bac)\b", "Bac", 0),
]

MOTS_ETABLISSEMENT = (
    r"(universite|university|ecole|school|institut|institute|faculte|faculty|"
    r"lycee|academy|academie|cnam|iut|esi|ensa|encg|est)"
)


def extraire_formations(section):
    """Reconstruit les diplômes obtenus, avec établissement et année."""
    if not section:
        return []

    formations = []
    for ligne in section.splitlines():
        brute = ligne.strip(" •-–—*\t")
        if len(brute) < 4:
            continue
        normalisee = _sans_accents(brute.lower())

        niveau = None
        for motif, libelle, _ in NIVEAUX:
            if re.search(motif, normalisee):
                niveau = libelle
                break
        etablissement = re.search(MOTS_ETABLISSEMENT + r"[^,;\n]{0,60}", normalisee)
        annee = re.search(r"(?:19|20)\d{2}", brute)

        if niveau or etablissement:
            formations.append({
                "level": niveau,
                "institution": etablissement.group().strip() if etablissement else None,
                "studyType": brute[:120],
                "endDate": annee.group() if annee else None,
            })

    return formations


def diplome_le_plus_eleve(formations, texte_complet=""):
    """Niveau le plus élevé, en se rabattant sur le texte entier si besoin."""
    rangs = {libelle: rang for _, libelle, rang in NIVEAUX}
    niveaux = [f["level"] for f in formations if f.get("level")]

    if not niveaux and texte_complet:
        normalise = _sans_accents(texte_complet.lower())
        niveaux = [lib for motif, lib, _ in NIVEAUX if re.search(motif, normalise)]

    if not niveaux:
        return None
    return max(niveaux, key=lambda n: rangs.get(n, -1))


# --------------------------------------------------------------------------
# Certifications et langues
# --------------------------------------------------------------------------

ORGANISMES = (
    r"(aws|microsoft|google|cisco|oracle|pmi|scrum\.org|scrum alliance|comptia|"
    r"ibm|red hat|linux foundation|isaca|axelos|itil|tosa|opquast)"
)


def extraire_certifications(section):
    if not section:
        return []
    certifications = []
    for ligne in section.splitlines():
        brute = ligne.strip(" •-–—*\t")
        if len(brute) < 5:
            continue
        organisme = re.search(ORGANISMES, _sans_accents(brute.lower()))
        annee = re.search(r"(?:19|20)\d{2}", brute)
        certifications.append({
            "name": re.sub(r"\s*\((?:19|20)\d{2}\)\s*", " ", brute)[:120].strip(),
            "issuer": organisme.group() if organisme else None,
            "date": annee.group() if annee else None,
        })
    return certifications


LANGUES_CONNUES = {
    "francais": "Français", "french": "Français",
    "anglais": "Anglais", "english": "Anglais",
    "arabe": "Arabe", "arabic": "Arabe",
    "espagnol": "Espagnol", "spanish": "Espagnol",
    "allemand": "Allemand", "german": "Allemand",
    "italien": "Italien", "italian": "Italien",
    "amazigh": "Amazigh", "chinois": "Chinois", "russe": "Russe",
}

# Niveaux ramenes au cadre europeen commun de reference (CECRL)
NIVEAUX_LANGUE = [
    (r"\b(c2|bilingue|bilingual|langue maternelle|native|natif|maternelle)\b", "C2"),
    (r"\b(c1|courant|fluent|avance|advanced)\b", "C1"),
    (r"\b(b2|bon niveau|professionnel|professional|intermediaire superieur)\b", "B2"),
    (r"\b(b1|intermediaire|intermediate|moyen)\b", "B1"),
    (r"\b(a2|elementaire|elementary|basique|basic)\b", "A2"),
    (r"\b(a1|debutant|beginner|notions)\b", "A1"),
]


def extraire_langues(section, texte_complet=""):
    """Langues avec leur niveau ramené à l'échelle CECRL."""
    source = section or texte_complet or ""
    langues = []
    vues = set()

    for ligne in source.splitlines():
        normalisee = _sans_accents(ligne.lower())
        for cle, libelle in LANGUES_CONNUES.items():
            if re.search(r"\b" + cle + r"\b", normalisee) and libelle not in vues:
                niveau = next(
                    (n for motif, n in NIVEAUX_LANGUE if re.search(motif, normalisee)), None
                )
                langues.append({"language": libelle, "fluency": niveau})
                vues.add(libelle)

    return langues


# --------------------------------------------------------------------------
# Compétences
# --------------------------------------------------------------------------

def extraire_competences(texte):
    """Compétences du référentiel présentes dans le texte, forme canonique."""
    normalise = _sans_accents((texte or "").lower())
    trouvees = []
    for variante in VARIANTES_TRIEES:
        motif = r"(?<![\w+#])" + re.escape(_sans_accents(variante)) + r"(?![\w+#])"
        if re.search(motif, normalise):
            canonique = INDEX_VARIANTES[variante]
            if canonique not in trouvees:
                trouvees.append(canonique)
    return trouvees


# --------------------------------------------------------------------------
# Profil complet
# --------------------------------------------------------------------------

def analyser_cv(texte):
    """Produit le profil structuré complet, au format normalisé.

    Le schéma reprend les blocs de JSON Resume (basics, work, education,
    skills, certificates, languages), auxquels s'ajoutent les agrégats
    utilisés par le moteur de score.
    """
    sections = decouper_en_sections(texte)

    experiences = extraire_experiences(sections.get("experience", ""))
    # Repli : certains CV ne comportent aucun en-tete identifiable.
    if not experiences and not sections.get("experience"):
        experiences = extraire_experiences(texte)

    formations = extraire_formations(sections.get("formation", ""))
    competences = extraire_competences(texte)
    langues = extraire_langues(sections.get("langues", ""), texte)

    # Les langues ne sont pas des competences techniques : on les separe.
    noms_langues = {_sans_accents(li["language"].lower()) for li in langues}
    competences_techniques = [c for c in competences if c not in noms_langues]

    return {
        "basics": extraire_identite(texte, sections.get("entete", "")),
        "work": experiences,
        "education": formations,
        "skills": competences_techniques,
        "certificates": extraire_certifications(sections.get("certifications", "")),
        "languages": langues,
        # Agregats consommes par le moteur de score
        "totalExperienceYears": annees_experience(experiences),
        "highestDegree": diplome_le_plus_eleve(formations, texte),
        "sectionsDetectees": [k for k, v in sections.items() if v and k != "entete"],
    }


def vers_profil_scoring(profil_ats):
    """Adapte le profil ATS au format attendu par le moteur de score."""
    return {
        "skills": profil_ats.get("skills", []),
        "experience_years": profil_ats.get("totalExperienceYears", 0),
        "degree": profil_ats.get("highestDegree"),
    }
