"""Domaine « administration » de l'assistant : la gouvernance de la plateforme.

L'administrateur et le recruteur n'ont pas les mêmes questions. Le second
demande qui recruter ; le premier demande qui a accès à quoi, ce qui attend
une décision et ce qui s'est passé sur la plateforme. Leur ouvrir le même
assistant reviendrait à répondre à côté dans un cas sur deux.

Une raison plus forte impose cette séparation. Le rôle administrateur ne
détient pas `view_applications` : le principe retenu dès le sprint 2 est
qu'un administrateur gère les comptes sans consulter les dossiers de
candidature. Si l'assistant lui restituait le contenu des candidatures parce
qu'il « voit tout », il contournerait par la conversation une restriction
posée dans le modèle de droits. Ce module existe donc autant pour répondre
utilement que pour ne pas trahir les permissions.

Le périmètre couvert ici est celui des permissions effectivement détenues
par le rôle : comptes et validations (`manage_users`), rôles et droits
(`manage_roles`), signalements (`view_signalements`), journal d'audit et
corbeille.
"""
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from ...models.journal import EntreeJournal
from ...models.job_offer import JobOffer
from ...models.permission import Permission
from ...models.role import Role
from ...models.signalement import Signalement
from ...models.user import User
from ..qualification_recruteur import qualifier
from .connaissance import Document

SUGGESTIONS = [
    "Combien de comptes attendent une validation ?",
    "Quels signalements restent à traiter ?",
    "Comment les comptes sont-ils répartis par rôle ?",
    "Que s'est-il passé récemment sur la plateforme ?",
    "Comment fonctionne la validation d'un compte recruteur ?",
]

LIBELLE_ROLE = {
    "admin": "Administrateur",
    "recruiter": "Recruteur",
    "candidate": "Candidat",
}

LIBELLE_ACTION = {
    "candidature_statut": "Changement de statut d'une candidature",
    "candidature_analysee": "Relance d'analyse",
    "signalement_traite": "Décision sur un signalement",
    "signalement_ouvert": "Signalement ouvert à la main",
    "evaluation_entretien": "Compte rendu d'entretien",
    "compte_valide": "Validation d'un compte",
    "compte_refuse": "Refus d'une demande",
    "compte_desactive": "Désactivation d'un compte",
    "compte_supprime": "Mise en corbeille d'un compte",
    "compte_restaure": "Restauration d'un compte",
    "permissions_modifiees": "Modification des permissions",
    "offre_publiee": "Publication d'une offre",
    "offre_supprimee": "Suppression d'une offre",
}

LIBELLE_SEVERITE = {
    "alerte": "Alerte", "attention": "Vigilance", "information": "Information",
}


def _maintenant():
    return datetime.now(timezone.utc)


def _naif(date):
    """Compare des dates dont certaines sont naïves selon leur origine."""
    return date.replace(tzinfo=None) if date and date.tzinfo else date


# --------------------------------------------------------------------------
# Faits chiffrés
# --------------------------------------------------------------------------

def faits():
    """Grandeurs de gouvernance, calculées et non déduites."""
    vivants = User.query.filter(User.deleted_at.is_(None)).all()
    corbeille = User.query.filter(User.deleted_at.isnot(None)).count()

    par_role = {}
    for u in vivants:
        cle = u.role.name if u.role else "inconnu"
        par_role.setdefault(cle, {"total": 0, "actifs": 0, "attente": 0, "refuses": 0})
        par_role[cle]["total"] += 1
        if u.status == "active" and u.is_active:
            par_role[cle]["actifs"] += 1
        elif u.status == "pending":
            par_role[cle]["attente"] += 1
        elif u.status == "rejected":
            par_role[cle]["refuses"] += 1

    signalements = Signalement.query.all()
    a_traiter = [s for s in signalements if s.statut in ("nouveau", "examine")]

    limite = _naif(_maintenant() - timedelta(days=7))
    traces = EntreeJournal.query.all()
    recentes = [t for t in traces if _naif(t.created_at) and _naif(t.created_at) >= limite]

    return {
        "comptes_total": len(vivants),
        "comptes_actifs": len([u for u in vivants if u.status == "active" and u.is_active]),
        "comptes_desactives": len([u for u in vivants if u.status == "active" and not u.is_active]),
        "comptes_en_attente": len([u for u in vivants if u.status == "pending"]),
        "comptes_refuses": len([u for u in vivants if u.status == "rejected"]),
        "comptes_en_corbeille": corbeille,
        "par_role": par_role,
        "offres_publiees": JobOffer.query.filter(JobOffer.deleted_at.is_(None)).count(),
        "offres_en_corbeille": JobOffer.query.filter(JobOffer.deleted_at.isnot(None)).count(),
        "signalements_total": len(signalements),
        "signalements_a_traiter": len(a_traiter),
        "signalements_alertes": len([s for s in a_traiter if s.severite == "alerte"]),
        "signalements_confirmes": len([s for s in signalements if s.statut == "confirme"]),
        "signalements_ecartes": len([s for s in signalements if s.statut == "ecarte"]),
        "signalements_manuels": len([s for s in signalements if s.origine == "manuel"]),
        "traces_total": len(traces),
        "traces_7_jours": len(recentes),
        "roles_total": Role.query.count(),
        "permissions_total": Permission.query.count(),
        "comptes_sous_tentatives": len([u for u in vivants if (u.failed_logins or 0) >= 3]),
    }


def texte_faits(f):
    """Contexte chiffré transmis au générateur, au même titre qu'une source."""
    lignes = [
        "FAITS VÉRIFIÉS (chiffres calculés sur la base de données) :",
        f"- Comptes : {f['comptes_total']} au total, dont {f['comptes_actifs']} actifs, "
        f"{f['comptes_en_attente']} en attente de validation, "
        f"{f['comptes_desactives']} désactivés et {f['comptes_refuses']} refusés.",
        f"- Corbeille : {f['comptes_en_corbeille']} compte(s), "
        f"{f['offres_en_corbeille']} offre(s).",
        f"- Offres publiées : {f['offres_publiees']}.",
        f"- Signalements : {f['signalements_total']} au total, "
        f"{f['signalements_a_traiter']} à traiter dont {f['signalements_alertes']} en alerte.",
        f"- Journal d'audit : {f['traces_total']} entrées, "
        f"{f['traces_7_jours']} sur les sept derniers jours.",
        f"- Droits : {f['roles_total']} rôles, {f['permissions_total']} permissions.",
    ]
    for nom, d in sorted(f["par_role"].items()):
        lignes.append(
            f"- Rôle {LIBELLE_ROLE.get(nom, nom)} : {d['total']} compte(s), "
            f"{d['actifs']} actif(s), {d['attente']} en attente."
        )
    if f["comptes_sous_tentatives"]:
        lignes.append(
            f"- {f['comptes_sous_tentatives']} compte(s) cumulent au moins trois "
            f"tentatives de connexion échouées."
        )
    return "\n".join(lignes)


# --------------------------------------------------------------------------
# Base de connaissance propre à l'administration
# --------------------------------------------------------------------------

AIDE = [
    (
        "admin-validation",
        "Valider ou refuser une demande de compte recruteur",
        """Un compte recruteur n'est pas actif à l'inscription : publier une offre engage
l'entreprise représentée, un administrateur doit donc approuver la demande. Tant qu'elle
n'est pas tranchée, la personne ne peut pas se connecter et voit un message le lui
expliquant.

Chaque demande est accompagnée d'un faisceau d'indices destiné à éclairer la décision :
la nature de l'adresse — domaine professionnel, messagerie grand public ou adresse
jetable —, le nombre de comptes déjà validés sur le même domaine, la ressemblance avec
un domaine connu, et la cohérence entre l'entreprise déclarée et le domaine.

Aucun de ces indices n'est bloquant, et ce choix est délibéré. Refuser les adresses
personnelles écarterait une part importante des petites entreprises, qui recrutent
souvent depuis une messagerie grand public, sans gêner un fraudeur capable d'acheter un
domaine. L'indice le plus utile reste la ressemblance avec un domaine déjà validé : une
adresse imitant à un caractère près celle d'une entreprise connue mérite une
vérification.

Un refus peut être accompagné d'un motif, transmis au demandeur lors de sa prochaine
tentative de connexion.""",
        "/admin/recruteurs",
    ),
    (
        "admin-permissions",
        "Rôles, permissions et application immédiate",
        """Les droits ne sont pas portés par le jeton de session mais relus en base de
données à chaque requête sensible. La conséquence est directe : lorsqu'une permission
est retirée à un rôle, la restriction s'applique à la requête suivante, sans attendre
l'expiration de la session des utilisateurs concernés.

Le rôle administrateur ne bénéficie d'aucun contournement : il ne peut agir que sur les
permissions qu'il détient explicitement. Deux d'entre elles ne peuvent lui être retirées
— la gestion des comptes et celle des rôles — faute de quoi la plateforme deviendrait
définitivement ingérable.

Un administrateur ne peut ni modifier son propre rôle, ni désactiver ou supprimer un
compte administrateur, ni supprimer son propre compte.""",
        "/admin/roles",
    ),
    (
        "admin-signalements",
        "Le contrôle des dossiers de candidature",
        """Des contrôles automatiques s'exécutent à chaque dépôt de candidature et à chaque
réanalyse. Ils portent sur quatre familles d'anomalies : la concordance entre l'identité
du compte et celle du document, les coordonnées déjà rattachées à un autre compte, les
documents dupliqués ou très proches d'un autre, et la cohérence interne du parcours.

Un signalement n'est jamais une preuve. Un nom d'épouse, une translittération ou un
curriculum rédigé par un cabinet déclenchent les mêmes contrôles qu'une usurpation.
Chaque observation porte donc le motif exact et les éléments qui l'ont déclenchée, et
attend une décision humaine : confirmée ou écartée, avec un motif obligatoire dans le
second cas.

Un signalement ne modifie ni la note ni le statut d'une candidature. Le score reste
inchangé et une marque distincte signale au recruteur qu'un point mérite vérification :
fusionner l'adéquation et la fiabilité dans un seul chiffre priverait le recruteur des
deux signaux.

Un recruteur peut également ouvrir un signalement à la main, pour ce que les contrôles
ne peuvent pas voir : un diplôme qui n'existe pas, une référence introuvable.""",
        "/signalements",
    ),
    (
        "admin-journal",
        "Le journal d'audit",
        """Le journal conserve la trace des actions significatives : changement de statut
d'une candidature, validation ou refus d'un compte, modification des permissions,
traitement d'un signalement, publication ou suppression d'une offre.

Trois propriétés en font un audit et non un simple historique. Les entrées sont
immuables : aucune route ne permet de les modifier ni de les supprimer. L'objet visé est
décrit par un couple type/identifiant plutôt que par une clé étrangère, de sorte que la
trace survive à la suppression de l'objet — c'est souvent après une suppression qu'on a
besoin de savoir qui l'a ordonnée. Enfin le nom de l'auteur est recopié dans l'entrée,
pour rester lisible même si le compte disparaît.

La liste des actions tracées est volontairement courte : tout journaliser reviendrait à
ne rien journaliser, le bruit noyant ce qui compte.""",
        "/admin/journal",
    ),
    (
        "admin-corbeille",
        "Suppression logique et corbeille",
        """La suppression d'un compte ou d'une offre est logique et non définitive :
l'élément part en corbeille, cesse d'être visible et actif, mais reste restaurable. Les
candidatures rattachées ne sont pas détruites, et l'historique reste cohérent.

La suppression définitive n'est possible que depuis la corbeille, en deux temps
délibérés. Un compte administrateur ne peut être ni supprimé ni purgé, et personne ne
peut supprimer son propre compte.""",
        "/admin/corbeille",
    ),
    (
        "admin-securite",
        "Sécurité des accès",
        """Les mots de passe sont stockés sous forme d'empreintes calculées avec bcrypt et
ne peuvent pas être relus. Une tentative de connexion échouée renvoie le même message
qu'une adresse inconnue : celui qui essaie des mots de passe n'apprend pas si le compte
existe.

Le compteur de tentatives est porté par le compte visé, et l'alerte est adressée à son
titulaire — c'est lui qui doit savoir qu'on essaie d'y entrer. Une connexion réussie
remet le compteur à zéro.

La déconnexion révoque le jeton présenté en l'inscrivant sur une liste de blocage : un
jeton volé après déconnexion ne vaut plus rien.""",
        "/admin/utilisateurs",
    ),
]


def _texte_demande(utilisateur, connus):
    """Décrit une demande en attente, indices de qualification compris."""
    q = qualifier(utilisateur, connus)
    parties = [
        f"Demande de compte recruteur de {utilisateur.full_name}.",
        f"Adresse : {utilisateur.email}.",
        f"Nature de l'adresse : {q['nature']}.",
        "Statut : en attente de validation par un administrateur.",
    ]
    if utilisateur.company:
        parties.append(f"Entreprise déclarée : {utilisateur.company}.")
    else:
        parties.append("Aucune entreprise déclarée : le champ est facultatif.")
    if utilisateur.phone:
        parties.append(f"Téléphone : {utilisateur.phone}.")
    if q["comptes_valides_sur_domaine"]:
        parties.append(
            f"{q['comptes_valides_sur_domaine']} compte(s) déjà validé(s) sur le "
            f"domaine {q['domaine']}."
        )
    parties.extend(q["indices"])
    parties.append(
        f"Demande déposée le {utilisateur.created_at.strftime('%d/%m/%Y')}."
    )
    return " ".join(parties)


def _texte_signalement(s):
    candidature = s.application
    candidat = candidature.candidate if candidature else None
    parties = [
        f"Signalement de type « {s.type} », gravité "
        f"{LIBELLE_SEVERITE.get(s.severite, s.severite).lower()}.",
        f"Origine : {s.origine}.",
        f"Statut : {s.statut}.",
        s.message,
    ]
    if candidat:
        parties.append(f"Dossier concerné : candidature de {candidat.full_name}.")
    return " ".join(parties)


def _texte_role(role):
    codes = sorted(p.code for p in role.permissions)
    effectif = User.query.filter_by(role_id=role.id).filter(
        User.deleted_at.is_(None)
    ).count()
    return (
        f"Rôle {LIBELLE_ROLE.get(role.name, role.name)} ({role.name}). "
        f"{effectif} compte(s) rattaché(s). "
        + (f"Permissions accordées : {', '.join(codes)}."
           if codes else "Aucune permission accordée.")
    )


def documents():
    """Base de connaissance du domaine administration.

    Les candidatures et les offres en sont volontairement absentes : le rôle
    administrateur ne détient pas `view_applications`, et l'assistant ne doit
    pas offrir par la conversation ce que le modèle de droits refuse.
    """
    docs = [
        Document(f"aide:{cle}", "aide", titre, texte, lien)
        for cle, titre, texte, lien in AIDE
    ]

    connus = User.query.filter(User.deleted_at.is_(None)).all()
    for u in connus:
        if u.status == "pending":
            docs.append(
                Document(
                    f"demande:{u.id}", "compte",
                    f"Demande de {u.full_name}",
                    _texte_demande(u, connus),
                    "/admin/recruteurs",
                    {"user_id": u.id},
                )
            )

    for s in Signalement.query.filter(
        Signalement.statut.in_(("nouveau", "examine"))
    ).all():
        docs.append(
            Document(
                f"signalement:{s.id}", "signalement",
                f"Signalement {s.type}",
                _texte_signalement(s),
                "/signalements",
                {"signalement_id": s.id, "severite": s.severite},
            )
        )

    for role in Role.query.all():
        docs.append(
            Document(
                f"role:{role.id}", "role",
                f"Rôle {LIBELLE_ROLE.get(role.name, role.name)}",
                _texte_role(role),
                "/admin/roles",
                {"role_id": role.id},
            )
        )

    return docs


def empreinte():
    """Signature de l'état, servant à invalider l'index."""
    derniere = EntreeJournal.query.order_by(EntreeJournal.id.desc()).first()
    return (
        "administration",
        User.query.count(),
        User.query.filter_by(status="pending").count(),
        Signalement.query.count(),
        Signalement.query.filter_by(statut="nouveau").count(),
        Role.query.count(),
        derniere.id if derniere else 0,
    )


# --------------------------------------------------------------------------
# Tableaux joints à la réponse
# --------------------------------------------------------------------------

def tableau(question):
    """Joint un tableau lorsque la question appelle une liste.

    Le tableau provient des données, jamais du texte généré : c'est lui qui
    fait foi si l'administrateur veut vérifier.
    """
    q = _normaliser(question)

    if re.search(r"attente|valider|validation|demande|approuv|recruteur", q):
        connus = User.query.filter(User.deleted_at.is_(None)).all()
        attente = sorted(
            [u for u in connus if u.status == "pending"], key=lambda u: u.created_at
        )
        if attente:
            return {
                "colonnes": ["Demandeur", "Adresse", "Nature du domaine", "Déposée le"],
                "lignes": [
                    [
                        u.full_name,
                        u.email,
                        qualifier(u, connus)["nature"],
                        u.created_at.strftime("%d/%m/%Y"),
                    ]
                    for u in attente
                ],
            }

    if re.search(r"signalement|anomalie|fraude|controle|suspect|alerte", q):
        ouverts = Signalement.query.filter(
            Signalement.statut.in_(("nouveau", "examine"))
        ).all()
        if ouverts:
            ordre = {"alerte": 0, "attention": 1, "information": 2}
            ouverts.sort(key=lambda s: ordre.get(s.severite, 3))
            return {
                "colonnes": ["Gravité", "Type", "Origine", "Dossier"],
                "lignes": [
                    [
                        LIBELLE_SEVERITE.get(s.severite, s.severite),
                        s.type.replace("_", " "),
                        s.origine,
                        (s.application.candidate.full_name
                         if s.application and s.application.candidate else "—"),
                    ]
                    for s in ouverts[:15]
                ],
            }

    if re.search(r"role|permission|droit|repartition|par role|effectif", q):
        f = faits()
        lignes = []
        for nom, d in sorted(f["par_role"].items()):
            lignes.append([
                LIBELLE_ROLE.get(nom, nom), d["total"], d["actifs"],
                d["attente"], d["refuses"],
            ])
        if lignes:
            return {
                "colonnes": ["Rôle", "Comptes", "Actifs", "En attente", "Refusés"],
                "lignes": lignes,
            }

    if re.search(r"journal|audit|historique|trace|recemment|passe|activite", q):
        traces = (
            EntreeJournal.query.order_by(EntreeJournal.created_at.desc())
            .limit(12).all()
        )
        if traces:
            return {
                "colonnes": ["Date", "Action", "Auteur", "Objet"],
                "lignes": [
                    [
                        t.created_at.strftime("%d/%m %H:%M"),
                        LIBELLE_ACTION.get(t.action, t.action),
                        t.auteur_nom or "Système",
                        t.objet_libelle or "—",
                    ]
                    for t in traces
                ],
            }

    if re.search(r"corbeille|supprime|restaur|purge", q):
        comptes = User.query.filter(User.deleted_at.isnot(None)).all()
        offres = JobOffer.query.filter(JobOffer.deleted_at.isnot(None)).all()
        lignes = [["Compte", u.full_name, u.deleted_at.strftime("%d/%m/%Y")]
                  for u in comptes]
        lignes += [["Offre", o.title, o.deleted_at.strftime("%d/%m/%Y")]
                   for o in offres]
        if lignes:
            return {
                "colonnes": ["Nature", "Libellé", "Supprimé le"],
                "lignes": lignes,
            }

    return None


def lien(question):
    """Écran vers lequel renvoyer, déduit de l'intention."""
    correspondances = [
        (r"attente|valider|validation|demande|approuv", "/admin/recruteurs",
         "Traiter les demandes"),
        (r"signalement|anomalie|fraude|controle", "/signalements",
         "Ouvrir le contrôle des dossiers"),
        (r"role|permission|droit", "/admin/roles", "Gérer les rôles"),
        (r"journal|audit|historique|trace", "/admin/journal", "Consulter le journal"),
        (r"corbeille|supprime|restaur", "/admin/corbeille", "Ouvrir la corbeille"),
        (r"compte|utilisateur", "/admin/utilisateurs", "Gérer les comptes"),
    ]
    q = _normaliser(question)
    for motif, href, libelle in correspondances:
        if re.search(motif, q):
            return {"href": href, "libelle": libelle}
    return None


# --------------------------------------------------------------------------
# Rédaction déterministe
# --------------------------------------------------------------------------

def _normaliser(texte):
    nfkd = unicodedata.normalize("NFKD", (texte or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


INTENTIONS = [
    ("salutation", r"^\s*(bonjour|bonsoir|salut|coucou|hello|hey|hi|yo|salam|slm)\b"),
    ("remerciement", r"\b(merci|thanks|thank you|nickel|parfait|super)\b"),
    ("adieu", r"\b(au revoir|bye|a bientot|bonne journee|bonne soiree)\b"),
    ("politesse", r"\b(ca va|comment vas[- ]tu|comment allez[- ]vous|tu vas bien)\b"),
    ("identite", r"(qui es[- ]tu|tu es qui|presente[- ]toi|es[- ]tu (une |un )?(ia|robot))"),
    ("capacites", r"(que (sais|peux)[- ]tu|tes capacites|a quoi sers[- ]tu|que puis[- ]je (te )?demander|aide[- ]moi|^\s*aide\s*$)"),  # noqa: E501

    ("validation", r"(attente|valider|validation|demande de compte|approuv|refus|recruteur a)"),
    ("signalements", r"(signalement|anomalie|fraude|controle des dossiers|suspect|usurpation)"),
    ("corbeille", r"(corbeille|supprime|restaur|purge)"),
    ("journal", r"(journal|audit|historique|trace|recemment|s'est passe|activite)"),
    ("securite", r"(securite|tentative|mot de passe|connexion echouee|intrusion|bcrypt|jeton|token)"),  # noqa: E501
    ("roles", r"(role|permission|droit|habilitation|acces)"),
    ("comptes", r"(compte|utilisateur|effectif|repartition|combien de personnes)"),
    ("bilan", r"(combien|nombre de|volume|statistique|chiffres|resume|bilan|situation|etat des lieux)"),  # noqa: E501
]

SOCIALES = {"salutation", "remerciement", "adieu", "politesse", "identite", "capacites"}


def intention(question):
    q = _normaliser(question)
    for nom, motif in INTENTIONS:
        if re.search(motif, q):
            return nom
    return "inconnue"


def _accord(n, singulier, pluriel=None):
    return singulier if n <= 1 else (pluriel or singulier + "s")


def _fiches(documents, limite=2):
    fiches = [d for d in documents if d.type == "aide"]
    return "\n\n".join(d.texte.strip() for d in fiches[:limite]) if fiches else None


def composer(question, documents, f):
    """Produit la réponse correspondant à l'intention reconnue."""
    nom = intention(question)

    if nom == "salutation":
        base = "Bonjour. Voici où en est la plateforme."
        points = []
        if f["comptes_en_attente"]:
            points.append(
                f"{f['comptes_en_attente']} "
                f"{_accord(f['comptes_en_attente'], 'demande')} de compte "
                f"{_accord(f['comptes_en_attente'], 'attend', 'attendent')} votre décision"
            )
        if f["signalements_a_traiter"]:
            points.append(
                f"{f['signalements_a_traiter']} "
                f"{_accord(f['signalements_a_traiter'], 'signalement')} "
                f"{_accord(f['signalements_a_traiter'], 'reste', 'restent')} à trancher"
            )
        if points:
            return base + " " + ", et ".join(points).capitalize() + "."
        return (
            "Bonjour. Rien n'attend de décision : aucune demande de compte en "
            "attente, aucun signalement ouvert."
        )

    if nom == "remerciement":
        return "Avec plaisir. N'hésitez pas si vous avez d'autres questions."
    if nom == "adieu":
        return "Bonne continuation. Je reste disponible."
    if nom == "politesse":
        return "Tout va bien, merci. Que souhaitez-vous vérifier sur la plateforme ?"

    if nom == "identite":
        return (
            "Je suis l'assistant de SkillSeek AI, en vue administration. Je réponds "
            "sur les comptes, les rôles et permissions, les signalements, le journal "
            "d'audit et la corbeille, en consultant directement la base. Je ne "
            "restitue pas le contenu des candidatures : le rôle administrateur ne "
            "détient pas ce droit, et je ne le contourne pas."
        )

    if nom == "capacites":
        return (
            "Je peux vous renseigner sur cinq choses.\n\n"
            "Les comptes : effectifs par rôle, demandes en attente de validation, "
            "comptes désactivés ou refusés.\n"
            "Les droits : quel rôle détient quelles permissions, et pourquoi un "
            "retrait s'applique immédiatement.\n"
            "Le contrôle des dossiers : signalements ouverts, gravité, origine "
            "automatique ou humaine.\n"
            "Le journal d'audit : ce qui s'est passé récemment et qui en est "
            "l'auteur.\n"
            "La corbeille : ce qui a été supprimé et reste restaurable.\n\n"
            "Posez votre question en langage courant."
        )

    if nom == "validation":
        if not f["comptes_en_attente"]:
            texte = "Aucune demande de compte n'attend de décision."
            if f["comptes_refuses"]:
                texte += (
                    f" {f['comptes_refuses']} "
                    f"{_accord(f['comptes_refuses'], 'demande')} "
                    f"{_accord(f['comptes_refuses'], 'a', 'ont')} été "
                    f"{_accord(f['comptes_refuses'], 'refusée')} par le passé."
                )
            return texte
        return (
            f"{f['comptes_en_attente']} "
            f"{_accord(f['comptes_en_attente'], 'demande')} de compte recruteur "
            f"{_accord(f['comptes_en_attente'], 'attend', 'attendent')} votre "
            f"décision. Le tableau ci-dessous indique pour chacune la nature du "
            f"domaine de l'adresse. Ces indices éclairent la décision sans la "
            f"remplacer : une messagerie grand public est fréquente chez les très "
            f"petites entreprises et ne constitue pas un motif de refus."
        )

    if nom == "signalements":
        if not f["signalements_total"]:
            return (
                "Aucun signalement n'a été relevé. Les contrôles s'exécutent à "
                "chaque dépôt de candidature et à chaque réanalyse."
            )
        if not f["signalements_a_traiter"]:
            return (
                f"Les {f['signalements_total']} signalements relevés ont tous été "
                f"tranchés : {f['signalements_confirmes']} confirmés, "
                f"{f['signalements_ecartes']} écartés."
            )
        return (
            f"{f['signalements_a_traiter']} "
            f"{_accord(f['signalements_a_traiter'], 'signalement')} "
            f"{_accord(f['signalements_a_traiter'], 'attend', 'attendent')} une "
            f"décision, dont {f['signalements_alertes']} en alerte. Un signalement "
            f"n'est pas une preuve : il porte le motif exact et les éléments qui "
            f"l'ont déclenché, et la note de la candidature reste inchangée."
        )

    if nom == "corbeille":
        total = f["comptes_en_corbeille"] + f["offres_en_corbeille"]
        if not total:
            return "La corbeille est vide."
        return (
            f"La corbeille contient {f['comptes_en_corbeille']} "
            f"{_accord(f['comptes_en_corbeille'], 'compte')} et "
            f"{f['offres_en_corbeille']} {_accord(f['offres_en_corbeille'], 'offre')}. "
            f"La suppression est logique : ces éléments restent restaurables, et les "
            f"candidatures rattachées n'ont pas été détruites."
        )

    if nom == "journal":
        if not f["traces_total"]:
            return "Le journal est vide : aucune action traçable n'a encore eu lieu."
        return (
            f"Le journal compte {f['traces_total']} "
            f"{_accord(f['traces_total'], 'entrée')}, dont {f['traces_7_jours']} sur "
            f"les sept derniers jours. Les entrées sont immuables : aucune route ne "
            f"permet de les modifier ni de les supprimer. Les plus récentes figurent "
            f"ci-dessous."
        )

    if nom == "securite":
        if f["comptes_sous_tentatives"]:
            return (
                f"{f['comptes_sous_tentatives']} "
                f"{_accord(f['comptes_sous_tentatives'], 'compte')} "
                f"{_accord(f['comptes_sous_tentatives'], 'cumule', 'cumulent')} au "
                f"moins trois tentatives de connexion échouées. Le compteur est porté "
                f"par le compte visé et l'alerte est adressée à son titulaire : celui "
                f"qui essaie des mots de passe n'apprend rien, le message d'erreur "
                f"étant identique pour une adresse inconnue."
            )
        return (
            "Aucun compte ne cumule de tentatives de connexion échouées. Les mots de "
            "passe sont stockés sous forme d'empreintes bcrypt et ne peuvent pas être "
            "relus ; la déconnexion révoque le jeton présenté."
        )

    if nom == "roles":
        details = ", ".join(
            f"{LIBELLE_ROLE.get(n, n)} : {d['total']}"
            for n, d in sorted(f["par_role"].items())
        )
        return (
            f"La plateforme compte {f['roles_total']} rôles et "
            f"{f['permissions_total']} permissions. Répartition des comptes — "
            f"{details}. Les permissions sont relues en base à chaque requête "
            f"sensible : un retrait de droit s'applique dès la requête suivante, "
            f"sans attendre l'expiration de la session concernée."
        )

    if nom in ("comptes", "bilan"):
        phrase = (
            f"La plateforme compte {f['comptes_total']} "
            f"{_accord(f['comptes_total'], 'compte')}, dont "
            f"{f['comptes_actifs']} {_accord(f['comptes_actifs'], 'actif')}"
        )
        if f["comptes_en_attente"]:
            phrase += f" et {f['comptes_en_attente']} en attente de validation"
        phrase += f". {f['offres_publiees']} "
        phrase += f"{_accord(f['offres_publiees'], 'offre')} "
        phrase += f"{_accord(f['offres_publiees'], 'est', 'sont')} publiée"
        phrase += "s." if f["offres_publiees"] > 1 else "."
        if f["signalements_a_traiter"]:
            phrase += (
                f" {f['signalements_a_traiter']} "
                f"{_accord(f['signalements_a_traiter'], 'signalement')} "
                f"{_accord(f['signalements_a_traiter'], 'reste', 'restent')} à traiter."
            )
        return phrase

    texte = _fiches(documents, limite=1)
    if texte:
        return texte

    return (
        "Je n'ai pas su rattacher votre question à ce que je sais faire.\n\n"
        "Je peux vous renseigner sur les comptes et les demandes en attente, les "
        "rôles et permissions, les signalements ouverts, le journal d'audit et la "
        "corbeille. Essayez par exemple : « combien de comptes attendent une "
        "validation ? », « quels signalements restent à traiter ? » ou « comment "
        "fonctionne la validation d'un compte recruteur ? »."
    )


RELANCES = {
    "salutation": ["Combien de comptes attendent une validation ?",
                   "Quels signalements restent à traiter ?",
                   "Que s'est-il passé récemment ?"],
    "capacites": ["Comment les comptes sont-ils répartis par rôle ?",
                  "Quels signalements restent à traiter ?",
                  "Comment fonctionne le journal d'audit ?"],
    "identite": ["Comment fonctionne la validation d'un compte recruteur ?",
                 "Pourquoi un retrait de permission s'applique-t-il immédiatement ?"],
    "validation": ["Comment sont qualifiées les demandes de compte ?",
                   "Combien de comptes ont été refusés ?"],
    "signalements": ["Un signalement modifie-t-il la note du candidat ?",
                     "Que s'est-il passé récemment sur la plateforme ?"],
    "roles": ["Pourquoi un retrait de permission s'applique-t-il immédiatement ?",
              "Comment les comptes sont-ils répartis par rôle ?"],
    "journal": ["Quelles actions sont tracées ?",
                "Quels signalements restent à traiter ?"],
    "securite": ["Comment les mots de passe sont-ils stockés ?",
                 "Combien de comptes sont désactivés ?"],
    "corbeille": ["Un compte supprimé est-il récupérable ?",
                  "Combien de comptes sont actifs ?"],
    "inconnue": ["Fais-moi un état des lieux de la plateforme",
                 "Combien de comptes attendent une validation ?",
                 "Quels signalements restent à traiter ?"],
}


def relances(question):
    return RELANCES.get(intention(question), RELANCES["inconnue"])
