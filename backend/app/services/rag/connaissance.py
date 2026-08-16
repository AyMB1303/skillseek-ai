"""Construction de la base de connaissance interrogeable par l'assistant.

Chaque élément de la plateforme est transformé en un document textuel
autonome : le texte doit se suffire à lui-même, car c'est lui qui sera
retrouvé puis transmis au générateur. Un document mentionnant « ce candidat »
sans le nommer serait inexploitable une fois sorti de son contexte.

Les documents portent des métadonnées (type, identifiant, lien) qui
permettent de citer les sources dans la réponse et de renvoyer l'utilisateur
vers l'écran concerné.
"""
from ...models.application import Application
from ...models.job_offer import JobOffer
from ...models.user import User
from ..scoring import PLAFOND_TOP, SEUIL_RETENU

LIBELLE_STATUT = {
    "received": "reçue, en attente de traitement",
    "under_review": "en cours d'étude",
    "shortlisted": "présélectionnée",
    "interview": "convoquée en entretien",
    "hired": "acceptée, candidat recruté",
    "rejected": "non retenue",
}


class Document:
    """Unité indexable : un texte, sa provenance et son lien de consultation."""

    def __init__(self, identifiant, type_, titre, texte, lien=None, donnees=None):
        self.identifiant = identifiant
        self.type = type_
        self.titre = titre
        self.texte = texte
        self.lien = lien
        self.donnees = donnees or {}

    def to_dict(self):
        return {
            "id": self.identifiant,
            "type": self.type,
            "titre": self.titre,
            "lien": self.lien,
        }


# --------------------------------------------------------------------------
# Documentation de la plateforme
#
# Ces textes permettent à l'assistant de répondre aux questions portant sur
# le fonctionnement du produit, et non sur les données. Sans eux, une
# question comme « comment fonctionne le score ? » resterait sans réponse.
# --------------------------------------------------------------------------

AIDE = [
    (
        "aide-score",
        "Comment le score de compatibilité est calculé",
        """Le score de compatibilité est une note sur 100 attribuée automatiquement à
chaque candidature. Il combine cinq composantes : la correspondance des compétences
obligatoires de l'offre (35 points), les compétences souhaitées (10 points), la
proximité sémantique entre le CV et le descriptif de l'offre (25 points), les années
d'expérience (20 points) et le niveau de diplôme (10 points).

Lorsqu'une composante ne peut pas être calculée, son poids est reporté sur les
compétences obligatoires, de sorte que le total reste toujours sur 100 et que les
candidatures demeurent comparables entre elles.

Les critères éliminatoires définis sur l'offre — expérience minimale, diplôme minimal,
compétence indispensable — plafonnent la note à 45 points. Le motif exact du
déclassement est conservé et affiché au recruteur.""",
        "/candidatures",
    ),
    (
        "aide-preselection",
        "La règle de présélection des candidatures",
        f"""Une candidature dont la note est inférieure à {SEUIL_RETENU} sur 100 est écartée du
classement, mais elle n'est jamais supprimée : elle reste consultable dans l'onglet
« Écartées » et le recruteur peut la repêcher à tout moment.

Parmi les candidatures ayant atteint le seuil, les {PLAFOND_TOP} meilleures notes
constituent la liste restreinte présentée en priorité. Ce nombre est un plafond et non
un objectif : si moins de {PLAFOND_TOP} candidatures atteignent le seuil, la liste ne
contient que celles-ci, sans remplissage artificiel.

La décision finale appartient toujours au recruteur : le système propose un
classement, il ne décide jamais du sort d'une candidature.""",
        "/candidatures",
    ),
    (
        "aide-analyse",
        "Comment un CV est analysé",
        """Le texte du CV est d'abord extrait directement du document. Si celui-ci est un
document numérisé, c'est-à-dire une suite d'images sans couche textuelle, une
reconnaissance optique de caractères prend le relais. Les formats PDF et Word sont
acceptés, dans la limite de 5 Mo.

Le document est ensuite découpé en sections — expérience, formation, compétences,
certifications, langues — puis chaque section est exploitée pour reconstituer un
profil structuré : coordonnées, postes occupés avec leur employeur et leurs dates,
diplômes, certifications et langues avec leur niveau.

La durée totale d'expérience est calculée à partir des périodes reconstituées, en
fusionnant celles qui se chevauchent : deux postes occupés simultanément ne sont pas
comptés deux fois.

Si le document ne peut pas être lu, la candidature est signalée comme dépourvue de
note — et non comme écartée — et le recruteur peut relancer l'analyse ou saisir le
profil manuellement.""",
        "/candidatures",
    ),
    (
        "aide-statuts",
        "Les statuts d'une candidature",
        """Une candidature suit les statuts suivants : reçue à son dépôt, en cours d'étude
lorsque le recruteur l'examine, présélectionnée lorsqu'elle est retenue pour la suite,
convoquée en entretien, puis acceptée ou non retenue.

Chaque changement de statut déclenche une notification adressée au candidat concerné,
qui suit ainsi l'avancement de son dossier sans avoir à contacter l'entreprise.""",
        "/candidatures",
    ),
    (
        "aide-roles",
        "Les rôles et les droits d'accès",
        """La plateforme distingue trois rôles. L'administrateur gère les comptes, les rôles
et les permissions. Le recruteur publie des offres, consulte les candidatures classées
et prend les décisions. Le candidat consulte les offres, dépose son CV et suit ses
candidatures.

Les permissions sont vérifiées en base de données à chaque requête sensible : lorsqu'un
administrateur retire un droit, la restriction s'applique immédiatement, sans attendre
l'expiration de la session de l'utilisateur concerné.

Les comptes recruteurs sont soumis à validation : publier une offre engage l'entreprise
représentée, un administrateur doit donc approuver la demande avant que le compte ne
devienne actif.""",
        "/admin/roles",
    ),
    (
        "aide-confidentialite",
        "Protection des données et supervision humaine",
        """Le candidat consent explicitement à l'analyse automatisée de son CV lors du dépôt.
Il peut à tout moment consulter, télécharger ou supprimer ses données depuis son espace
personnel.

Aucune décision définitive n'est prise par le système seul : le score est une aide à la
décision, et chaque étape est validée par un recruteur. Toute candidature écartée
automatiquement reste consultable et peut être repêchée.

Le score attribué n'est pas communiqué au candidat : il relève de l'appréciation interne
du recruteur.""",
        "/profil",
    ),
]


def documents_aide():
    return [
        Document(f"aide:{cle}", "aide", titre, texte, lien)
        for cle, titre, texte, lien in AIDE
    ]


# --------------------------------------------------------------------------
# Documents issus des données de la plateforme
# --------------------------------------------------------------------------

def _texte_offre(offre):
    parties = [
        f"Offre d'emploi : {offre.title}.",
        f"Statut : {'ouverte aux candidatures' if offre.status == 'open' else 'fermée'}.",
    ]
    # L'entreprise est portee par le compte du recruteur, pas par l'offre.
    if offre.recruiter and offre.recruiter.company:
        parties.append(f"Entreprise : {offre.recruiter.company}.")
    if offre.location:
        parties.append(f"Lieu : {offre.location}.")
    if offre.contract_type:
        parties.append(f"Type de contrat : {offre.contract_type}.")
    if offre.remote_policy:
        parties.append(f"Mode de travail : {offre.remote_policy}.")
    if offre.salaire_affiche:
        parties.append(f"Rémunération : {offre.salaire_affiche}.")
    if offre.required_skills:
        parties.append(
            "Compétences obligatoires : " + ", ".join(offre.required_skills) + "."
        )
    if offre.preferred_skills:
        parties.append(
            "Compétences souhaitées : " + ", ".join(offre.preferred_skills) + "."
        )
    if offre.min_experience_years:
        parties.append(f"Expérience minimale exigée : {offre.min_experience_years} ans.")
    if offre.min_degree:
        parties.append(f"Diplôme minimal exigé : {offre.min_degree}.")

    nb = len(offre.applications)
    notes = [c.score for c in offre.applications if c.score is not None]
    parties.append(f"Cette offre a reçu {nb} candidature(s).")
    if notes:
        parties.append(
            f"Note moyenne des candidatures : {round(sum(notes) / len(notes))} sur 100."
        )
        parties.append(
            f"{len([n for n in notes if n >= SEUIL_RETENU])} candidature(s) "
            f"atteignent le seuil de présélection."
        )
    parties.append(f"Description du poste : {offre.description}")
    return " ".join(parties)


def _texte_candidature(candidature):
    candidat = candidature.candidate
    offre = candidature.offer
    nom = candidat.full_name if candidat else "Candidat inconnu"
    intitule = offre.title if offre else "offre inconnue"

    parties = [
        f"Candidature de {nom} pour le poste de {intitule}.",
        f"Statut : {LIBELLE_STATUT.get(candidature.status, candidature.status)}.",
    ]

    if candidature.score is None:
        parties.append("Cette candidature n'a pas de note : le CV n'a pas pu être analysé.")
    else:
        parties.append(f"Note de compatibilité : {candidature.score} sur 100.")
        if candidature.score >= 70:
            parties.append("Ce profil est considéré comme très adapté à l'offre.")
        elif candidature.score >= SEUIL_RETENU:
            parties.append("Ce profil atteint le seuil de présélection.")
        else:
            parties.append("Ce profil est écarté du classement automatique.")

    details = candidature.score_details or {}
    ats = details.get("profil_ats") or {}

    if ats.get("totalExperienceYears") is not None:
        parties.append(f"Expérience : {ats['totalExperienceYears']} ans.")
    if ats.get("highestDegree"):
        parties.append(f"Diplôme : {ats['highestDegree']}.")
    if ats.get("skills"):
        parties.append("Compétences relevées : " + ", ".join(ats["skills"][:15]) + ".")
    for poste in (ats.get("work") or [])[:3]:
        if poste.get("position"):
            employeur = f" chez {poste['company']}" if poste.get("company") else ""
            parties.append(f"Poste occupé : {poste['position']}{employeur}.")
    for langue in (ats.get("languages") or []):
        if langue.get("fluency"):
            parties.append(f"Langue : {langue['language']} niveau {langue['fluency']}.")

    if details.get("competences_trouvees"):
        parties.append(
            "Compétences obligatoires satisfaites : "
            + ", ".join(details["competences_trouvees"]) + "."
        )
    if details.get("competences_manquantes"):
        parties.append(
            "Compétences obligatoires absentes : "
            + ", ".join(details["competences_manquantes"]) + "."
        )
    for motif in details.get("eliminatoires", []):
        parties.append(f"Critère éliminatoire : {motif}.")

    parties.append(
        f"Candidature déposée le {candidature.created_at.strftime('%d/%m/%Y')}."
    )
    return " ".join(parties)


def construire(portee_recruteur=None):
    """Assemble la base de connaissance.

    `portee_recruteur` limite les offres et candidatures à celles d'un
    recruteur donné : l'assistant ne doit jamais restituer des informations
    hors du périmètre de l'utilisateur qui l'interroge.
    """
    documents = documents_aide()

    offres = JobOffer.query.filter(JobOffer.deleted_at.is_(None))
    if portee_recruteur is not None:
        offres = offres.filter(JobOffer.recruiter_id == portee_recruteur)

    identifiants_offres = []
    for offre in offres.all():
        identifiants_offres.append(offre.id)
        documents.append(
            Document(
                f"offre:{offre.id}",
                "offre",
                offre.title,
                _texte_offre(offre),
                f"/offres/{offre.id}",
                {"offre_id": offre.id},
            )
        )

    candidatures = Application.query
    if portee_recruteur is not None:
        if not identifiants_offres:
            return documents
        candidatures = candidatures.filter(Application.offer_id.in_(identifiants_offres))

    for candidature in candidatures.all():
        documents.append(
            Document(
                f"candidature:{candidature.id}",
                "candidature",
                candidature.candidate.full_name if candidature.candidate else "Candidature",
                _texte_candidature(candidature),
                "/candidatures",
                {
                    "candidature_id": candidature.id,
                    "score": candidature.score,
                    "statut": candidature.status,
                    "offre_id": candidature.offer_id,
                },
            )
        )

    return documents


def empreinte(portee_recruteur=None):
    """Signature de l'état des données, servant à invalider l'index.

    Recalculer les vecteurs à chaque question serait coûteux ; les
    recalculer jamais donnerait des réponses périmées. Cette empreinte
    change dès qu'une donnée pertinente est modifiée.
    """
    offres = JobOffer.query
    candidatures = Application.query
    if portee_recruteur is not None:
        offres = offres.filter(JobOffer.recruiter_id == portee_recruteur)

    derniere = (
        Application.query.order_by(Application.id.desc()).first()
    )
    return (
        portee_recruteur,
        offres.count(),
        candidatures.count(),
        derniere.id if derniere else 0,
        derniere.status if derniere else "",
        User.query.count(),
    )
