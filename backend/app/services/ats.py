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

from .competences import INDEX_VARIANTES, VARIANTES_TRIEES, canoniser

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


# Rubriques qui s'ecrivent couramment « Intitule : contenu » sur une seule
# ligne. Les autres reclament un en-tete isole.
SECTIONS_EN_LIGNE = ("langues", "competences", "certifications", "interets")


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
    """Renvoie ``(section, reste)`` si la ligne est un en-tête, sinon ``None``.

    ``reste`` est le contenu qui suit l'intitulé sur la même ligne. De
    nombreux CV compacts écrivent « Langues : Français (courant), Anglais
    (courant) » d'un seul tenant : traiter cette ligne comme du texte
    ordinaire faisait disparaître la section, et l'extraction se rabattait
    alors sur le document entier.
    """
    brute = ligne.strip()
    if not brute or len(brute) > 200:
        return None

    # En-tete seul sur sa ligne : forme la plus courante.
    if len(brute) <= 60:
        nettoyee = _sans_accents(brute.lower()).strip(" :–—-•\t")
        nettoyee = re.sub(r"[^a-z' ]", "", nettoyee).strip()
        for section, intitules in EN_TETES.items():
            if nettoyee in intitules:
                return section, ""

    # En-tete suivi de son contenu sur la meme ligne, separes par « : ».
    # Restreint aux rubriques enumeratives : « Projet : refonte du portail »
    # ou « Formation : Coursera » sont des lignes de contenu, pas des
    # en-tetes, et les prendre pour tels interromprait la rubrique en cours.
    tete, separateur, reste = brute.partition(":")
    if separateur and len(tete) <= 60:
        nettoyee = _sans_accents(tete.lower()).strip(" –—-•\t")
        nettoyee = re.sub(r"[^a-z' ]", "", nettoyee).strip()
        for section in SECTIONS_EN_LIGNE:
            if nettoyee in EN_TETES[section]:
                return section, reste.strip()

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
            courante, reste = detectee
            sections.setdefault(courante, [])
            if reste:
                sections[courante].append(reste)
            continue
        sections.setdefault(courante, []).append(ligne)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


# --------------------------------------------------------------------------
# Identité et coordonnées
# --------------------------------------------------------------------------

# Les quantificateurs sont bornes, et non libres. Un CV est un texte fourni
# par un tiers : avec « [\w.+-]+ », une ligne faite de mots et de points sans
# arobase oblige le moteur a reexaminer la meme suite depuis chaque position,
# soit un cout quadratique en longueur de ligne. Les bornes retenues sont
# celles de la RFC 5321 : 64 caracteres pour la partie locale, 63 par etiquette
# de domaine. Aucune adresse legitime n'est perdue.
MOTIF_EMAIL = r"[\w.+-]{1,64}@[\w-]{1,63}(?:\.[\w-]{1,63}){1,4}"
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
        # L'adresse electronique est retiree de la ligne avant le decoupage.
        # Elle voisine souvent le numero sans separateur — « +212 6 37 72 13 28
        # aymen@exemple.ma » — et le fragment entier etait alors ecarte comme
        # etant une adresse : le telephone n'etait jamais releve.
        ligne = re.sub(MOTIF_EMAIL, " ", ligne)
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

# Separateurs frequents entre intitule de poste et employeur.
#
# Le motif attend des espaces simples : la ligne est normalisee juste avant le
# decoupage. Ecrit « \s+…\s+ », il devenait quadratique sur les suites
# d'espaces d'alignement que produit l'extraction d'un PDF, le moteur essayant
# chaque coupure possible de la suite avant de conclure a l'echec.
SEPARATEURS_POSTE = r" (?:chez|at|@|au sein de|-|–|—|\||,) "

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
            # Espaces internes ramenes a un seul : SEPARATEURS_POSTE attend
            # des espaces simples, et l'extraction d'un PDF laisse souvent des
            # suites d'espaces d'alignement au milieu d'une ligne.
            nettoye = re.sub(r"\s+", " ", candidat.strip(" •-–—*\t"))
            if re.search(MOTS_POSTE, _sans_accents(nettoye.lower())):
                morceaux = re.split(SEPARATEURS_POSTE, nettoye, maxsplit=1)
                entree["position"] = morceaux[0].strip()
                if len(morceaux) > 1:
                    entree["company"] = morceaux[1].strip()
                break
        entree["summary"] = " ".join(entree["summary"])[:400]
        entree.pop("_ligne_source", None)

    return entrees


# « 6 ans d'experience », « experience : 4 ans », « 5+ years of experience ».
# Ces tournures figurent dans le resume de tete de nombreux curriculums.
MOTIFS_ANNEES_ANNONCEES = [
    r"(\d{1,2})\s*\+?\s*(?:ans?|annees?|years?)\s*(?:of\s*)?(?:d[e']\s*)?experience",
    r"experience\s*(?:professionnelle\s*)?[:\-]?\s*(\d{1,2})\s*\+?\s*(?:ans?|years?)",
    r"(\d{1,2})\s*\+?\s*(?:ans?|years?)\s*(?:dans|en|d[e'])",
]


def annees_annoncees(texte):
    """Anciennete que le candidat declare en toutes lettres, si elle existe.

    Repli employe lorsque aucune periode datee n'a pu etre reconstruite. Un
    curriculum qui ecrit « Ingenieur, 6 ans d'experience » sans dater ses
    postes produisait jusqu'ici zero annee d'experience — donc, l'exigence
    d'anciennete etant un critere eliminatoire, une candidature ecartee sur
    une information que le document contenait pourtant.

    Le defaut est silencieux : rien ne distingue « ce candidat n'a aucune
    experience » de « je n'ai pas su lire ses dates ». C'est exactement le
    genre d'ecart que ce projet s'attache a ne pas laisser passer sans le
    nommer.

    On retient la plus grande valeur trouvee, et jamais plus de 45 ans : au
    dela, le nombre lu vient d'autre chose que d'une anciennete.
    """
    normalise = _sans_accents((texte or "").lower())
    valeurs = []
    for motif in MOTIFS_ANNEES_ANNONCEES:
        valeurs += [int(v) for v in re.findall(motif, normalise)]
    valeurs = [v for v in valeurs if 0 < v <= 45]
    return max(valeurs) if valeurs else 0


def mois_experience(experiences):
    """Durée totale en mois, sans compter deux fois les postes simultanés.

    Le detail au mois est conserve parce que l'arrondi a l'annee efface
    precisement ce qui distingue un debutant d'un candidat sans experience :
    deux mois de stage et zero mois s'ecrivent tous deux « 0 an ». Le moteur
    continue de raisonner en annees — c'est l'unite des offres — mais
    l'interface et les motifs de rejet disposent de la mesure exacte.
    """
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
    return min(total, 45 * 12)


def annees_experience(experiences):
    """Durée totale en années entières, telle que la comparent les offres."""
    return round(mois_experience(experiences) / 12)


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
        # L'annee entre parentheses est retiree du libelle, puis les espaces
        # laisses par ce retrait sont refermes. En deux passes plutot qu'un
        # seul motif encadre de « \s* » : place en tete, ce quantificateur
        # libre faisait reexaminer chaque suite d'espaces depuis toutes ses
        # positions, pour un cout quadratique en longueur de ligne.
        sans_annee = re.sub(r"\((?:19|20)\d{2}\)", " ", brute)
        certifications.append({
            "name": re.sub(r"\s{2,}", " ", sans_annee).strip()[:120],
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
    # « maternel » comme « maternelle » : le CV accorde avec la langue citee
    # (« Arabe (Maternel) »), pas avec le mot « langue ».
    (r"\b(c2|bilingue|bilingual|native|natif|native speaker|"
     r"(?:langue\s+)?maternel(?:le)?)\b", "C2"),
    (r"\b(c1|courant|fluent|avance|advanced)\b", "C1"),
    (r"\b(b2|bon niveau|professionnel|professional|intermediaire superieur)\b", "B2"),
    (r"\b(b1|intermediaire|intermediate|moyen)\b", "B1"),
    (r"\b(a2|elementaire|elementary|basique|basic)\b", "A2"),
    (r"\b(a1|debutant|beginner|notions)\b", "A1"),
]


# Separateurs entre deux langues d'une meme ligne : « Francais (courant),
# Anglais (B2) · Arabe ». Le decoupage permet d'attribuer a chaque langue le
# niveau qui la suit, au lieu d'appliquer a toutes le premier niveau rencontre
# sur la ligne.
SEPARATEURS_LANGUE = re.compile(r"[,;|•·/]|\s+[-–—]\s+|\s{3,}")

# Mention explicite d'une rubrique de langues. « langages » — rubrique de
# langages de programmation — ne doit surtout pas correspondre.
MENTION_LANGUES = re.compile(r"\blangues?\b|\blanguages?\b|\bmaitrise des langues\b")


def _niveau_langue(fragment):
    normalise = _sans_accents((fragment or "").lower())
    for motif, niveau in NIVEAUX_LANGUE:
        if re.search(motif, normalise):
            return niveau
    return None


def extraire_langues(section, texte_complet=""):
    """Langues avec leur niveau ramené à l'échelle CECRL.

    Deux régimes, et la distinction est délibérée :

    * une rubrique « Langues » a été identifiée — tout ce qu'elle contient
      est une déclaration de langue, on la lit telle quelle ;
    * aucune rubrique — on ne parcourt le document entier qu'à la condition
      que la ligne se présente elle-même comme une déclaration de langues.
      Sans cette réserve, « Arabe » cité dans le nom d'un employeur ou d'une
      école suffisait à faire apparaître une langue que le candidat n'a
      jamais revendiquée. Un profil enrichi de ce que le document ne dit pas
      n'est pas une commodité : c'est une erreur d'extraction, et elle se
      paie au moment où le recruteur compare le profil au CV.
    """
    avec_rubrique = bool(section and section.strip())
    source = section if avec_rubrique else (texte_complet or "")

    langues = []
    vues = set()

    for ligne in source.splitlines():
        normalisee = _sans_accents(ligne.lower())
        if not avec_rubrique and not MENTION_LANGUES.search(normalisee):
            continue

        niveau_ligne = _niveau_langue(ligne)
        for fragment in SEPARATEURS_LANGUE.split(ligne):
            fragment_normalise = _sans_accents(fragment.lower())
            for cle, libelle in LANGUES_CONNUES.items():
                if libelle in vues:
                    continue
                if re.search(r"\b" + cle + r"\b", fragment_normalise):
                    # Le niveau accole a la langue prime ; a defaut, celui de
                    # la ligne, qui vaut alors pour toutes les langues citees.
                    langues.append({
                        "language": libelle,
                        "fluency": _niveau_langue(fragment) or niveau_ligne,
                    })
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

    # Competences etayees : celles que le candidat fait apparaitre dans le
    # recit de ce qu'il a fait, et non seulement dans sa liste de competences.
    #
    # La distinction n'est pas cosmetique. Une rubrique « Competences » est
    # declarative : elle coute une ligne a ecrire et n'engage a rien. Un poste
    # decrit engage une periode, un employeur et une activite. Un curriculum
    # peut donc satisfaire toutes les exigences d'une offre sans qu'aucune ne
    # soit adossee a une experience — c'est precisement le profil qu'un
    # recruteur ecarte d'un coup d'oeil et qu'un moteur fonde sur les mots
    # retient.
    #
    # On ne juge pas ici : on distingue. Ce que le score en fait est decide
    # dans « scoring.py », et une competence declaree n'est jamais niee.
    # `summary` est une chaine une fois l'entree consolidee, une liste de
    # lignes tant qu'elle se construit. Un « join » applique a une chaine
    # insere un espace entre chaque *caractere* — « F l a s k » — et aucune
    # competence n'y est plus reconnaissable. Le defaut ne levait aucune
    # erreur : il rendait simplement l'etayage nul pour tout le monde, ce qui
    # ressemblait a un resultat plutot qu'a une panne.
    def _texte(valeur):
        if isinstance(valeur, str):
            return valeur
        return " ".join(valeur or [])

    etayees = []
    for poste in experiences:
        entete = " ".join(filter(None, [poste.get("position"), poste.get("company")]))
        for phrase in re.split(r"[.;]\s+", _texte(poste.get("summary")) or ""):
            if not _situee(phrase):
                continue
            for c in extraire_competences(entete + " " + phrase):
                if c not in noms_langues and c not in etayees:
                    etayees.append(c)

    certifications = extraire_certifications(sections.get("certifications", ""))

    # Ce que le document dit, et ce qu'il ne dit pas.
    #
    # Une rubrique vide et une rubrique absente ne sont pas la meme
    # information, et les confondre est une faute d'analyse. L'interface qui
    # masque une rubrique vide laisse croire que la question ne s'est pas
    # posee ; celle qui affiche « aucune » laisse croire que le candidat a
    # declare n'en avoir aucune. Le profil porte donc, pour chaque rubrique,
    # ce que l'on sait : la rubrique figurait-elle dans le document, et
    # combien d'elements en a-t-on tires.
    #
    # « presente » se lit : un intitule de rubrique a ete reconnu dans le CV.
    # « elements » : ce que l'extraction en a retire. Les deux se lisent
    # ensemble — presente sans element signale une rubrique que le document
    # annonce mais que l'analyse n'a pas su lire, et c'est precisement le cas
    # ou le recruteur doit ouvrir le document lui-meme.
    contenus = {
        "experience": experiences,
        "formation": formations,
        "competences": competences_techniques,
        "certifications": certifications,
        "langues": langues,
    }
    rubriques = {
        nom: {
            "presente": bool(sections.get(nom, "").strip()),
            "elements": len(elements),
        }
        for nom, elements in contenus.items()
    }

    # L'experience a-t-elle pu etre etablie ?
    #
    # Zero an et « nous n'avons pas su lire » se ressemblent une fois ecrits
    # dans la meme case. Le premier est une mesure, le second un aveu, et le
    # candidat qui se voit ecarter pour « 0 an d'experience » merite de savoir
    # lequel des deux lui est oppose.
    mois_dates = mois_experience(experiences)
    annees_datees = round(mois_dates / 12)
    annees_dites = annees_annoncees(texte)
    experience_determinee = bool(experiences) or annees_dites > 0

    return {
        "basics": extraire_identite(texte, sections.get("entete", "")),
        "work": experiences,
        "education": formations,
        "skills": competences_techniques,
        "skillsEtayees": etayees,
        "certificates": certifications,
        "languages": langues,
        "rubriques": rubriques,
        "experienceDeterminee": experience_determinee,
        # Agregats consommes par le moteur de score.
        #
        # Le repli sur l'anciennete annoncee n'intervient que si aucune
        # periode datee n'a pu etre reconstruite : une valeur lue dans une
        # phrase ne doit jamais l'emporter sur des dates effectivement
        # presentes, qui sont verifiables.
        "totalExperienceYears": annees_datees or annees_dites,
        # Mesure exacte, en mois : elle seule permet de dire « deux mois »
        # plutot que « zero an ». Nulle quand aucune periode datee n'a ete lue.
        "totalExperienceMonths": mois_dates or (annees_dites * 12),
        "highestDegree": diplome_le_plus_eleve(formations, texte),
        "sectionsDetectees": [k for k, v in sections.items() if v and k != "entete"],
    }


def vers_profil_scoring(profil_ats):
    """Adapte le profil ATS au format attendu par le moteur de score."""
    return {
        "skills": profil_ats.get("skills", []),
        # Absente lorsque le profil est saisi a la main : le moteur traite
        # alors toutes les competences comme etayees, faute de recit ou les
        # chercher. Un profil saisi n'est pas penalise pour une distinction
        # que sa forme ne permet pas d'etablir.
        "skills_etayees": profil_ats.get("skillsEtayees"),
        "experience_years": profil_ats.get("totalExperienceYears", 0),
        # Faux uniquement lorsque le document ne porte ni periode datee ni
        # anciennete annoncee. Le moteur s'en sert pour ne pas ecarter un
        # candidat sur une mesure qui n'a pas eu lieu. Absent du dictionnaire
        # — profil saisi a la main — vaut « determinee » : le recruteur qui
        # saisit zero annee le fait sciemment.
        "experience_determinee": profil_ats.get("experienceDeterminee", True),
        "experience_months": profil_ats.get("totalExperienceMonths"),
        "degree": profil_ats.get("highestDegree"),
    }


# --------------------------------------------------------------------------
# Pratique ou entourage : ce que la phrase dit du role du candidat
# --------------------------------------------------------------------------
#
# Une premiere version tenait une competence pour etayee des lors que son nom
# figurait dans un poste occupe. Un jeu de cas ecrit par un tiers a montre la
# limite : « Validation documentaire des rapports de securite des clusters
# Kubernetes » creditait Kubernetes autant que « Mise en place d'un cluster
# Kubernetes ». Le mecanisme voyait le mot, pas ce que la personne en avait
# fait — et cinq candidatures sur cinq passaient.
#
# Les curriculums francais nominalisent l'action : ils ecrivent « Conception
# de… », « Pilotage de… », rarement « j'ai concu ». Deux lexiques suffisent
# donc, et ils sont volontairement courts : une liste longue donne l'illusion
# de la couverture et multiplie les faux positifs.
#
# La regle penche du cote du candidat. En l'absence de tout indice — ni
# pratique ni entourage — la competence reste creditee : on ne retire rien sur
# un silence. Seule la presence explicite d'un terme d'entourage, sans aucun
# terme de pratique dans la meme phrase, fait basculer.
#
# C'est une heuristique lexicale, avec les limites d'une heuristique : elle
# reconnait « validation » et « pilotage », elle ne reconnait pas « generation
# via des plugins d'exportation ». Nommer un role demande de lire la phrase,
# pas d'y chercher des mots.

TERMES_PRATIQUE = {
    "conception", "concu", "developpement", "developpe", "mise", "oeuvre",
    "implementation", "implemente", "realisation", "realise", "deploiement",
    "deploye", "industrialisation", "automatisation", "automatise",
    "optimisation", "optimise", "migration", "migre", "refonte",
    "administration", "administre", "exploitation", "exploite", "maintenance",
    "integration", "integre", "ecriture", "ecrit", "creation", "cree",
    "construction", "configuration", "configure", "parametrage",
    "programmation", "modelisation", "traitement", "extraction", "entrainement",
    "correction", "corrige", "reprise",
}

TERMES_ENTOURAGE = {
    "pilotage", "pilote", "coordination", "coordonne", "animation", "anime",
    "validation", "valide", "suivi", "supervision", "supervise", "redaction",
    "redige", "participation", "contribution", "accompagnement", "veille",
    "presentation", "recueil", "approbation", "approuve", "revue",
    "sensibilisation", "assistance", "reunion", "reunions", "comite",
    "comites", "ticket", "tickets", "documentaire",
}


def _situee(phrase):
    """La phrase décrit-elle une pratique, ou seulement un entourage ?"""
    mots = set(re.findall(r"[a-z]+", sans_accents(phrase.lower())))
    if mots & TERMES_PRATIQUE:
        return True
    if mots & TERMES_ENTOURAGE:
        return False
    return True          # aucun indice : le doute profite au candidat


# --------------------------------------------------------------------------
# Experience adossee aux competences du poste
# --------------------------------------------------------------------------

def experience_pertinente(profil_ats, competences_requises):
    """Part de la carriere qui touche reellement aux competences exigees.

    Le moteur comptait l'anciennete brute : huit ans de carriere valaient huit
    ans, quel qu'en soit le contenu. Un profil du bon domaine mais au parcours
    hors sujet en tirait donc la totalite des points d'experience, alors que
    c'est precisement ce que le recruteur regarde en premier.

    Chaque poste occupe est ici pondere par la **part des competences exigees
    que sa description fait apparaitre**. Un poste ou l'on decrit trois des
    quatre competences demandees compte pour trois quarts de sa duree ; un
    poste ou l'on n'en decrit aucune ne compte pas. La mesure separe nettement
    les deux populations du jeu de validation : 29 % de la carriere retenue
    pour les profils au vocabulaire sans le parcours, 73 a 78 % pour les
    autres.

    C'est une *part*, donc elle ne desavantage pas les profils juniors : un
    candidat a deux ans entierement consacres au sujet garde ses deux ans.

    Retourne (annees_ponderees, part_de_la_carriere).
    """
    cles = {
        (canoniser(c) or (c or "").lower())
        for c in (competences_requises or [])
    }
    if not cles:
        return profil_ats.get("totalExperienceYears", 0), 1.0

    mois_ponderes = mois_totaux = 0.0
    for poste in profil_ats.get("work") or []:
        resume = poste.get("summary")
        recit = resume if isinstance(resume, str) else " ".join(resume or [])
        entete = " ".join(filter(None, [poste.get("position"), poste.get("company")]))
        mois = poste.get("months") or 0
        mois_totaux += mois
        # Seules les phrases decrivant une pratique comptent : un poste passe
        # a valider et a coordonner n'adosse pas la competence a une experience.
        decrites = set()
        for phrase in re.split(r"[.;]\s+", recit or ""):
            if _situee(phrase):
                decrites |= cles & set(extraire_competences(entete + " " + phrase))
        mois_ponderes += mois * (len(decrites) / len(cles))

    part = mois_ponderes / mois_totaux if mois_totaux else 1.0
    return mois_ponderes / 12, part
