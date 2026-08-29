"""Détection d'anomalies sur les candidatures (S4-06).

Une plateforme de recrutement reçoit des documents qu'elle ne peut pas
vérifier : rien n'empêche un candidat de déposer le curriculum vitæ d'un
autre, de réutiliser celui d'un collègue, ou d'antidater une expérience. Ce
module relève les incohérences observables et les porte à la connaissance du
recruteur.

**Ce que le module ne fait pas**, et ne doit jamais faire : conclure. Aucun
contrôle ici ne prouve une fraude. Un nom d'épouse, une translittération de
l'arabe vers l'alphabet latin, un curriculum rédigé par un cabinet de
placement produiront des signalements parfaitement légitimes et parfaitement
innocents. C'est pourquoi un signalement ne modifie ni la note, ni le statut
de la candidature : il ouvre une vérification humaine, il ne la remplace pas.

Les contrôles se répartissent en quatre familles :

  1. **Cohérence entre le compte et le document** — le nom, l'adresse
     électronique et le téléphone déclarés à l'inscription correspondent-ils
     à ceux qui figurent dans le curriculum ?
  2. **Unicité du document** — ce curriculum a-t-il déjà été déposé, à
     l'identique ou presque, par quelqu'un d'autre ?
  3. **Cohérence interne** — les dates du parcours sont-elles possibles ?
  4. **Nature du fichier** — le document est-il bien ce qu'il prétend être,
     et ne transporte-t-il pas de contenu actif ?
"""
import hashlib
import logging
import os
import re
from datetime import date

from ..extensions import db
from ..models.application import Application
from ..models.user import User
from .ats import sans_accents

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Outils de comparaison
# --------------------------------------------------------------------------

MOTS_VIDES_NOM = {"el", "al", "ben", "ould", "de", "du", "da", "van", "bin", "abd"}


def _mots_du_nom(valeur):
    """Réduit un nom à ses composantes comparables.

    Les particules sont écartées : « El Amrani » et « Amrani » désignent la
    même personne dans l'usage courant, et les retenir produirait un écart
    artificiel.
    """
    normalise = sans_accents((valeur or "").lower())
    normalise = re.sub(r"[^a-z\s'-]", " ", normalise).replace("-", " ").replace("'", " ")
    return {m for m in normalise.split() if len(m) > 1 and m not in MOTS_VIDES_NOM}


def concordance_des_noms(nom_compte, nom_document):
    """Part des composantes du nom communes aux deux sources, dans [0, 1].

    La comparaison porte sur des ensembles de mots, non sur des chaînes :
    « Tazi Youssef » et « Youssef Tazi » sont la même personne, alors qu'une
    comparaison caractère par caractère les jugerait très éloignés.
    """
    a, b = _mots_du_nom(nom_compte), _mots_du_nom(nom_document)
    if not a or not b:
        return None                      # comparaison impossible, pas d'écart
    return len(a & b) / min(len(a), len(b))


def empreinte_texte(texte):
    """Empreinte stable du contenu, insensible à la mise en forme.

    Deux exports du même curriculum diffèrent par leurs espaces et leurs
    retours à la ligne : les normaliser avant de calculer l'empreinte permet
    de reconnaître le document malgré ces variations.
    """
    normalise = re.sub(r"\s+", " ", sans_accents((texte or "").lower())).strip()
    return hashlib.sha256(normalise.encode("utf-8")).hexdigest()


def _chiffres(valeur):
    return re.sub(r"\D", "", valeur or "")


# --------------------------------------------------------------------------
# 1. Cohérence entre le compte et le document
# --------------------------------------------------------------------------

SEUIL_CONCORDANCE_ALERTE = 0.34   # aucune composante commune sur trois
SEUIL_CONCORDANCE_DOUTE = 0.67    # une composante sur deux diverge


def _controler_identite(candidature, profil):
    signalements = []
    compte = candidature.candidate
    if compte is None:
        return signalements

    basics = (profil or {}).get("basics") or {}
    nom_document = basics.get("name")

    # --- Nom ---
    concordance = concordance_des_noms(compte.full_name, nom_document)
    if concordance is not None and concordance < SEUIL_CONCORDANCE_DOUTE:
        grave = concordance < SEUIL_CONCORDANCE_ALERTE
        signalements.append({
            "type": "identite_divergente",
            "severite": "alerte" if grave else "attention",
            "message": (
                f"Le curriculum est au nom de « {nom_document} », le compte au nom "
                f"de « {compte.full_name} »."
            ),
            "details": {
                "nom_compte": compte.full_name,
                "nom_document": nom_document,
                "concordance": round(concordance, 2),
                "lecture": (
                    "Aucune composante du nom n'est commune aux deux sources."
                    if grave else
                    "Une partie du nom concorde : changement de nom ou "
                    "translittération possible."
                ),
            },
        })

    # --- Adresse electronique ---
    email_document = (basics.get("email") or "").strip().lower()
    email_compte = (compte.email or "").strip().lower()
    if email_document and email_document != email_compte:
        # Cas nettement plus serieux : l'adresse appartient a un autre compte.
        with db.session.no_autoflush:
            proprietaire = User.query.filter_by(email=email_document).first()
        if proprietaire and proprietaire.id != compte.id:
            signalements.append({
                "type": "email_tiers",
                "severite": "alerte",
                "message": (
                    f"L'adresse figurant dans le curriculum est celle du compte "
                    f"de {proprietaire.full_name}."
                ),
                "details": {
                    "email_document": email_document,
                    "email_compte": email_compte,
                    "compte_rattache": proprietaire.full_name,
                },
            })
        else:
            signalements.append({
                "type": "email_divergent",
                "severite": "information",
                "message": (
                    "L'adresse électronique du curriculum diffère de celle du compte."
                ),
                "details": {
                    "email_document": email_document,
                    "email_compte": email_compte,
                    "lecture": (
                        "Fréquent et sans gravité : adresse personnelle sur le "
                        "document, professionnelle sur le compte."
                    ),
                },
            })

    # --- Telephone deja rattache a quelqu'un d'autre ---
    telephone = _chiffres(basics.get("phone"))
    if len(telephone) >= 9:
        suffixe = telephone[-9:]
        # `no_autoflush` est indispensable ici : les controles s'executent
        # pendant l'analyse, alors que la candidature n'est pas encore ecrite
        # en base. Sans cette precaution, la moindre lecture declencherait un
        # vidage prematuré de la session sur un objet incomplet.
        with db.session.no_autoflush:
            comptes = User.query.filter(
                User.id != compte.id,
                User.phone.isnot(None),
                User.deleted_at.is_(None),
            ).all()
        for autre in comptes:
            if _chiffres(autre.phone).endswith(suffixe):
                signalements.append({
                    "type": "telephone_partage",
                    "severite": "attention",
                    "message": (
                        f"Le numéro du curriculum est déjà rattaché au compte de "
                        f"{autre.full_name}."
                    ),
                    "details": {
                        "telephone_document": basics.get("phone"),
                        "compte_rattache": autre.full_name,
                    },
                })
                break

    return signalements


# --------------------------------------------------------------------------
# 2. Unicité du document
# --------------------------------------------------------------------------

def _controler_unicite(candidature, empreinte):
    """Repère un document déjà déposé par un autre candidat."""
    if not empreinte:
        return []

    # Idem : la candidature en cours d'analyse n'est pas encore persistee.
    with db.session.no_autoflush:
        jumelle = (
            Application.query
            .filter(
                Application.cv_empreinte == empreinte,
                Application.id != (candidature.id or -1),
                Application.candidate_id != candidature.candidate_id,
            )
            .first()
        )
    if jumelle is None:
        return []

    autre = jumelle.candidate.full_name if jumelle.candidate else "un autre candidat"
    return [{
        "type": "document_duplique",
        "severite": "alerte",
        "message": (
            f"Ce curriculum est identique, mot pour mot, à celui déposé par {autre}."
        ),
        "details": {
            "candidature_jumelle": jumelle.id,
            "candidat_jumeau": autre,
            "lecture": (
                "Deux personnes distinctes ont déposé le même document. L'une "
                "des deux candidatures repose sur le parcours de l'autre."
            ),
        },
    }]


# --------------------------------------------------------------------------
# 3. Cohérence interne du parcours
# --------------------------------------------------------------------------

MARGE_STAGE = 1          # un poste peut precede le diplome d'un an (stage, alternance)
AGE_MINIMAL_TRAVAIL = 16


def _annee(valeur):
    if not valeur:
        return None
    correspondance = re.search(r"(19|20)\d{2}", str(valeur))
    return int(correspondance.group()) if correspondance else None


def _controler_chronologie(profil):
    signalements = []
    postes = (profil or {}).get("work") or []
    formations = (profil or {}).get("education") or []
    annee_courante = date.today().year

    debuts = [_annee(p.get("startDate")) for p in postes]
    debuts = [a for a in debuts if a]

    # --- Dates situees dans le futur ---
    futures = [a for a in debuts if a > annee_courante]
    if futures:
        signalements.append({
            "type": "chronologie_incoherente",
            "severite": "attention",
            "message": f"Le parcours mentionne une expérience débutant en {max(futures)}.",
            "details": {"annees_futures": sorted(futures),
                        "annee_courante": annee_courante},
        })

    # --- Premier emploi anterieur au diplome le plus ancien ---
    diplomes = [_annee(f.get("endDate")) for f in formations]
    diplomes = [a for a in diplomes if a]
    if debuts and diplomes:
        premier_poste, premier_diplome = min(debuts), min(diplomes)
        ecart = premier_diplome - premier_poste
        if ecart > MARGE_STAGE:
            signalements.append({
                "type": "chronologie_incoherente",
                "severite": "information",
                "message": (
                    f"Le parcours professionnel débute en {premier_poste}, soit "
                    f"{ecart} ans avant le premier diplôme mentionné "
                    f"({premier_diplome})."
                ),
                "details": {
                    "premier_poste": premier_poste,
                    "premier_diplome": premier_diplome,
                    "ecart_annees": ecart,
                    "lecture": (
                        "Souvent explicable : reprise d'études, alternance, "
                        "emploi étudiant. À vérifier si l'écart est important."
                    ),
                },
            })

    # --- Duree totale invraisemblable ---
    experience = (profil or {}).get("totalExperienceYears") or 0
    if debuts and experience:
        amplitude = annee_courante - min(debuts) + 1
        if experience > amplitude + MARGE_STAGE:
            signalements.append({
                "type": "chronologie_incoherente",
                "severite": "attention",
                "message": (
                    f"L'expérience totale déclarée ({experience} ans) dépasse la "
                    f"durée réellement couverte par le parcours ({amplitude} ans)."
                ),
                "details": {
                    "experience_calculee": experience,
                    "amplitude_du_parcours": amplitude,
                    "lecture": "Postes simultanés déclarés comme successifs.",
                },
            })

    return signalements


# --------------------------------------------------------------------------
# 4. Nature du fichier
# --------------------------------------------------------------------------

SIGNATURES = {
    ".pdf": b"%PDF",
    ".docx": b"PK\x03\x04",
    ".doc": b"\xd0\xcf\x11\xe0",
}

# Elements actifs d'un PDF : rien de tout cela n'a sa place dans un curriculum.
MOTIFS_ACTIFS = (b"/JavaScript", b"/JS", b"/OpenAction", b"/Launch", b"/EmbeddedFile")

TAILLE_MAXIMALE = 12 * 1024 * 1024


def _controler_fichier(chemin):
    signalements = []
    if not chemin or not os.path.exists(chemin):
        return signalements

    extension = os.path.splitext(chemin)[1].lower()
    try:
        taille = os.path.getsize(chemin)
        with open(chemin, "rb") as flux:
            entete = flux.read(8)
            flux.seek(0)
            debut = flux.read(400_000)      # les elements actifs figurent en tete
    except OSError as erreur:
        logger.warning("Lecture du fichier impossible (%s)", erreur)
        return signalements

    # --- L'extension correspond-elle au contenu reel ? ---
    attendue = SIGNATURES.get(extension)
    if attendue and not entete.startswith(attendue):
        signalements.append({
            "type": "fichier_suspect",
            "severite": "alerte",
            "message": (
                f"Le fichier porte l'extension {extension} mais son contenu n'en "
                f"a pas la signature."
            ),
            "details": {
                "extension": extension,
                "signature_lue": entete[:4].hex(),
                "lecture": (
                    "Un fichier renommé pour paraître inoffensif présente cette "
                    "signature-là."
                ),
            },
        })

    # --- Contenu actif ---
    if extension == ".pdf":
        trouves = [m.decode() for m in MOTIFS_ACTIFS if m in debut]
        if trouves:
            signalements.append({
                "type": "fichier_suspect",
                "severite": "alerte",
                "message": "Le document PDF contient du code exécutable.",
                "details": {
                    "elements": trouves,
                    "lecture": (
                        "Un curriculum n'a aucune raison d'embarquer du script "
                        "ou une action automatique. Ne pas ouvrir hors d'un "
                        "lecteur à jour."
                    ),
                },
            })

    if taille > TAILLE_MAXIMALE:
        signalements.append({
            "type": "fichier_suspect",
            "severite": "information",
            "message": f"Le fichier pèse {taille // (1024 * 1024)} Mo.",
            "details": {"taille_octets": taille},
        })

    return signalements


# --------------------------------------------------------------------------
# 5. Indices de rédaction assistée
# --------------------------------------------------------------------------
#
# Ce controle est le plus fragile des cinq, et il est presente comme tel. Les
# outils de detection de texte genere se trompent souvent, et ils se trompent
# surtout au detriment des personnes qui n'ecrivent pas dans leur langue
# maternelle — exactement la population de candidats concernee ici. Il ne
# produit donc jamais qu'une « information », jamais une alerte, et son
# libelle dit explicitement qu'un curriculum soigne declenche les memes
# indices qu'un curriculum genere.

FORMULES_PASSE_PARTOUT = (
    "force de proposition", "esprit d'equipe", "dynamique et motive",
    "excellente capacite", "sens du detail", "passionne par",
    "solide experience", "environnement stimulant", "rigoureux et organise",
    "capacite d'adaptation", "excellent relationnel",
)

PRODUCTEURS_AUTOMATIQUES = ("skia/pdf", "chromium", "headless", "wkhtmltopdf", "puppeteer")


def _controler_redaction(texte, chemin):
    indices = []

    normalise = sans_accents((texte or "").lower())

    # --- Densite de formules creuses ---
    formules = [f for f in FORMULES_PASSE_PARTOUT if f in normalise]
    if len(formules) >= 3:
        indices.append(f"{len(formules)} formules passe-partout")

    # --- Uniformite des phrases ---
    phrases = [p.strip() for p in re.split(r"[.\n]", texte or "") if len(p.strip()) > 25]
    if len(phrases) >= 8:
        longueurs = [len(p) for p in phrases]
        moyenne = sum(longueurs) / len(longueurs)
        ecart = (sum((x - moyenne) ** 2 for x in longueurs) / len(longueurs)) ** 0.5
        if moyenne and ecart / moyenne < 0.25:
            indices.append("phrases de longueur anormalement régulière")

    # --- Absence totale de donnees concretes ---
    #
    # Quantificateurs bornes et groupe non capturant. Ecrit « \d+\s* », le
    # motif etait quadratique : sur une suite de chiffres suivie d'espaces, le
    # moteur reessayait chaque decoupage depuis chaque position avant de
    # conclure a l'echec. Le controle s'applique a des textes de plus de 800
    # caracteres issus de fichiers televerses, ou la depense se paie.
    # La classe « \s » est conservee plutot que « [ \t] » : la typographie
    # francaise place une espace insecable devant le signe pour cent, et les
    # PDF la restituent telle quelle.
    if len(texte or "") > 800 and not re.search(
        r"\d{1,12}\s{0,4}(?:%|k€|MAD|clients?|projets?)", texte or ""
    ):
        indices.append("aucun résultat chiffré")

    # --- Producteur du fichier ---
    if chemin and os.path.exists(chemin) and chemin.lower().endswith(".pdf"):
        try:
            with open(chemin, "rb") as flux:
                entete = flux.read(200_000).lower()
            for producteur in PRODUCTEURS_AUTOMATIQUES:
                if producteur.encode() in entete:
                    indices.append(f"produit par un outil automatisé ({producteur})")
                    break
        except OSError:
            pass

    if len(indices) < 2:
        return []

    return [{
        "type": "redaction_assistee",
        "severite": "information",
        "message": "Le document présente des indices de rédaction assistée.",
        "details": {
            "indices": indices,
            "lecture": (
                "Indice faible et non probant. Un curriculum soigné, relu ou "
                "rédigé par un cabinet de placement produit les mêmes signaux. "
                "Ne doit jamais motiver à lui seul un écartement."
            ),
        },
    }]


# --------------------------------------------------------------------------
# Point d'entrée
# --------------------------------------------------------------------------

def analyser(candidature, texte=None, profil=None, chemin=None):
    """Passe une candidature au crible et renvoie la liste des signalements.

    Aucun contrôle n'interrompt les autres : une défaillance isolée ne doit pas
    priver le recruteur des observations restantes.
    """
    chemin = chemin or candidature.cv_path
    empreinte = empreinte_texte(texte) if texte else None

    signalements = []
    controles = (
        ("identité", lambda: _controler_identite(candidature, profil)),
        ("unicité", lambda: _controler_unicite(candidature, empreinte)),
        ("chronologie", lambda: _controler_chronologie(profil)),
        ("fichier", lambda: _controler_fichier(chemin)),
        ("rédaction", lambda: _controler_redaction(texte, chemin)),
    )

    for nom, controle in controles:
        try:
            signalements.extend(controle())
        except Exception as erreur:      # noqa: BLE001 - un controle ne bloque pas les autres
            logger.warning("Contrôle « %s » en échec : %s", nom, erreur)

    return signalements, empreinte


def severite_maximale(signalements):
    """Gravité la plus élevée d'un ensemble, pour l'affichage synthétique."""
    ordre = {"information": 0, "attention": 1, "alerte": 2}
    if not signalements:
        return None
    return max(signalements, key=lambda s: ordre.get(s.get("severite"), 0))["severite"]
