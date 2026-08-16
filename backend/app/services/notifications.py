"""Création des notifications selon les événements de la plateforme.

Chaque événement cible un destinataire précis, ce qui matérialise la
séparation des rôles : un candidat ne reçoit que ce qui concerne ses
candidatures, un recruteur que ce qui concerne ses offres, un
administrateur que ce qui concerne la gestion des comptes.
"""
from ..extensions import db
from ..models.notification import Notification
from ..models.role import Role

# Libellés lisibles des statuts, du point de vue du candidat
MESSAGES_STATUT = {
    "under_review": "Votre candidature pour « {offre} » est en cours d'étude.",
    "shortlisted": "Bonne nouvelle : votre candidature pour « {offre} » a été présélectionnée.",
    "interview": "Vous êtes convoqué(e) à un entretien pour « {offre} ».",
    "hired": "Félicitations : votre candidature pour « {offre} » a été acceptée.",
    "rejected": "Votre candidature pour « {offre} » n'a pas été retenue.",
    "received": "Votre candidature pour « {offre} » a bien été reçue.",
}


def _creer(user_id, type_, message, link=None):
    db.session.add(Notification(user_id=user_id, type=type_, message=message, link=link))


def _utilisateurs_du_role(nom_role):
    role = Role.query.filter_by(name=nom_role).first()
    if role is None:
        return []
    return [u for u in role.users if u.is_active]


# --------------------------- Événements ---------------------------

def candidature_recue(candidature):
    """Nouvelle candidature -> notifie le recruteur propriétaire de l'offre."""
    offre = candidature.offer
    if offre is None:
        return

    message = (
        f"{candidature.candidate.full_name} a postulé à « {offre.title} »."
    )
    destinataires = set()

    if offre.recruiter_id:
        destinataires.add(offre.recruiter_id)
    # Filet de securite : si l'offre n'a pas de proprietaire actif, on informe
    # l'ensemble des recruteurs pour qu'aucune candidature ne reste orpheline.
    if not destinataires:
        destinataires = {u.id for u in _utilisateurs_du_role("recruiter")}

    for uid in destinataires:
        _creer(uid, "candidature_recue", message, "/candidatures")


def statut_change(candidature, ancien_statut):
    """Changement de statut -> notifie le candidat concerné."""
    if candidature.status == ancien_statut:
        return
    modele = MESSAGES_STATUT.get(candidature.status)
    if not modele:
        return

    offre = candidature.offer.title if candidature.offer else "une offre"
    _creer(
        candidature.candidate_id,
        "statut_change",
        modele.format(offre=offre),
        "/mes-candidatures",
    )


def compte_cree(nouvel_utilisateur, auteur=None):
    """Création de compte -> notifie les administrateurs (sauf l'auteur)."""
    role = nouvel_utilisateur.role.name if nouvel_utilisateur.role else "utilisateur"
    message = (
        f"Nouveau compte créé : {nouvel_utilisateur.full_name} ({role})."
    )
    for admin in _utilisateurs_du_role("admin"):
        if auteur and admin.id == auteur.id:
            continue  # inutile de se notifier soi-meme
        _creer(admin.id, "compte_cree", message, "/admin/utilisateurs")


def permissions_modifiees(role, auteur=None):
    """Modification des droits -> notifie les utilisateurs du rôle et les admins."""
    message_utilisateur = (
        f"Vos droits d'accès ont été mis à jour par un administrateur "
        f"({len(role.permissions)} permission(s) active(s))."
    )
    for u in role.users:
        if u.is_active:
            _creer(u.id, "permissions_modifiees", message_utilisateur, "/profil")

    message_admin = f"Les permissions du rôle « {role.name} » ont été modifiées."
    for admin in _utilisateurs_du_role("admin"):
        if auteur and admin.id == auteur.id:
            continue
        _creer(admin.id, "permissions_modifiees", message_admin, "/admin/roles")


def recruteur_en_attente(utilisateur):
    """Demande de compte recruteur -> notifie les administrateurs."""
    entreprise = f" ({utilisateur.company})" if utilisateur.company else ""
    message = (
        f"Demande de compte recruteur : {utilisateur.full_name}{entreprise} "
        f"attend une validation."
    )
    for admin in _utilisateurs_du_role("admin"):
        _creer(admin.id, "recruteur_en_attente", message, "/admin/recruteurs")


def compte_approuve(utilisateur, approbateur=None):
    """Validation d'un compte -> notifie le recruteur concerné et les admins."""
    _creer(
        utilisateur.id,
        "compte_approuve",
        "Votre compte recruteur a été validé. Vous pouvez désormais publier des offres.",
        "/dashboard",
    )
    message = f"Le compte de {utilisateur.full_name} a été validé."
    for admin in _utilisateurs_du_role("admin"):
        if approbateur and admin.id == approbateur.id:
            continue
        _creer(admin.id, "compte_approuve", message, "/admin/recruteurs")


def compte_refuse(utilisateur, motif=None):
    """Refus d'une demande -> notifie le demandeur avec le motif."""
    texte = "Votre demande de compte recruteur n'a pas été retenue."
    if motif:
        texte += f" Motif : {motif}"
    _creer(utilisateur.id, "compte_refuse", texte, "/connexion")


def compte_supprime(utilisateur, auteur=None):
    """Suppression d'un compte -> notifie les autres administrateurs."""
    message = f"Le compte de {utilisateur.full_name} a été placé en corbeille."
    for admin in _utilisateurs_du_role("admin"):
        if auteur and admin.id == auteur.id:
            continue
        _creer(admin.id, "compte_supprime", message, "/admin/corbeille")


def offre_publiee(offre):
    """Publication d'une offre -> notifie les administrateurs (suivi d'activité)."""
    auteur = offre.recruiter.full_name if offre.recruiter else "un recruteur"
    message = f"{auteur} a publié l'offre « {offre.title} »."
    for admin in _utilisateurs_du_role("admin"):
        _creer(admin.id, "offre_publiee", message, "/admin/utilisateurs")


# --------------------------------------------------------------------------
# Cycle de vie du compte et signaux d'attention
# --------------------------------------------------------------------------

# Au-dela de cette note, la candidature merite d'etre vue sans attendre le
# parcours habituel : le recruteur en est averti immediatement.
SEUIL_EXCELLENCE = 85

# Nombre d'echecs consecutifs a partir duquel le titulaire du compte est
# prevenu. En deca, l'alerte serait bruyante pour une simple faute de frappe.
SEUIL_TENTATIVES = 3


def bienvenue(utilisateur):
    """Inscription -> accueille le nouvel arrivant et l'oriente."""
    if utilisateur.status == "pending":
        texte = (
            "Bienvenue sur SkillSeek AI. Votre compte recruteur est en cours de "
            "validation ; vous serez averti dès qu'il sera activé."
        )
        lien = "/profil"
    elif utilisateur.role and utilisateur.role.name == "recruiter":
        texte = (
            "Bienvenue sur SkillSeek AI. Publiez votre première offre pour "
            "commencer à recevoir des candidatures analysées automatiquement."
        )
        lien = "/offres"
    else:
        texte = (
            "Bienvenue sur SkillSeek AI. Complétez votre profil, puis postulez "
            "aux offres qui vous correspondent : votre CV sera analysé "
            "automatiquement."
        )
        lien = "/offres"

    _creer(utilisateur.id, "bienvenue", texte, lien)


def score_eleve(candidature):
    """Note remarquable -> signale la candidature au recruteur sans délai."""
    if candidature.score is None or candidature.score < SEUIL_EXCELLENCE:
        return
    offre = candidature.offer
    if offre is None or not offre.recruiter_id:
        return

    nom = candidature.candidate.full_name if candidature.candidate else "Un candidat"
    _creer(
        offre.recruiter_id,
        "score_eleve",
        f"Profil remarquable : {nom} obtient {round(candidature.score)}/100 "
        f"sur « {offre.title} ».",
        "/candidatures",
    )


def compte_desactive(utilisateur, auteur=None):
    """Désactivation -> prévient l'intéressé et les autres administrateurs."""
    _creer(
        utilisateur.id,
        "compte_desactive",
        "Votre compte a été désactivé. Contactez un administrateur pour en "
        "connaître le motif.",
        "/connexion",
    )
    message = f"Le compte de {utilisateur.full_name} a été désactivé."
    for admin in _utilisateurs_du_role("admin"):
        if (auteur and admin.id == auteur.id) or admin.id == utilisateur.id:
            continue
        _creer(admin.id, "compte_desactive", message, "/admin/utilisateurs")


def compte_reactive(utilisateur, auteur=None):
    """Réactivation -> prévient l'intéressé, qui peut de nouveau se connecter."""
    _creer(
        utilisateur.id,
        "compte_reactive",
        "Votre compte a été réactivé. Vous pouvez de nouveau vous connecter.",
        "/dashboard",
    )


def compte_restaure(utilisateur, auteur=None):
    """Restauration depuis la corbeille -> prévient l'intéressé et les admins."""
    _creer(
        utilisateur.id,
        "compte_restaure",
        "Votre compte a été restauré et redevient accessible.",
        "/dashboard",
    )
    message = f"Le compte de {utilisateur.full_name} a été restauré."
    for admin in _utilisateurs_du_role("admin"):
        if (auteur and admin.id == auteur.id) or admin.id == utilisateur.id:
            continue
        _creer(admin.id, "compte_restaure", message, "/admin/corbeille")


def connexions_echouees(utilisateur, tentatives):
    """Échecs répétés -> avertit le titulaire du compte.

    La notification part vers le compte visé, jamais vers l'auteur des
    tentatives : elle informe la victime potentielle sans rien révéler à qui
    essaie de deviner un mot de passe.
    """
    if tentatives < SEUIL_TENTATIVES:
        return
    _creer(
        utilisateur.id,
        "connexions_echouees",
        f"{tentatives} tentatives de connexion ont échoué sur votre compte. "
        f"Si vous n'en êtes pas à l'origine, changez votre mot de passe.",
        "/profil",
    )


# --------------------------------------------------------------------------
# Contrôle des candidatures
# --------------------------------------------------------------------------

# Familles de signalements qui relevent de la securite du systeme, et non de
# la seule appreciation du recruteur : elles remontent aussi aux administrateurs.
TYPES_CRITIQUES = ("fichier_suspect", "email_tiers", "document_duplique")

LIBELLES_SIGNALEMENT = {
    "identite_divergente": "identité divergente",
    "email_divergent": "adresse électronique divergente",
    "email_tiers": "adresse appartenant à un autre compte",
    "telephone_partage": "numéro déjà rattaché à un autre compte",
    "document_duplique": "document identique à une autre candidature",
    "document_similaire": "document proche d'une autre candidature",
    "chronologie_incoherente": "chronologie incohérente",
    "redaction_assistee": "indices de rédaction assistée",
    "fichier_suspect": "fichier suspect",
    "diplome_douteux": "diplôme douteux",
    "experience_invraisemblable": "expérience invraisemblable",
    "references_fausses": "références introuvables",
    "autre": "anomalie signalée par le recruteur",
}


def signalements_ouverts(candidature, signalements):
    """Anomalies relevées -> avertit le recruteur, et l'administrateur si besoin.

    Un seul message par candidature, quel que soit le nombre d'anomalies : en
    envoyer un par contrôle noierait l'information utile.
    """
    if not signalements:
        return

    offre = candidature.offer
    nom = candidature.candidate.full_name if candidature.candidate else "Un candidat"
    intitule = offre.title if offre else "une offre"

    graves = [s for s in signalements if s.get("severite") == "alerte"]
    motifs = ", ".join(
        LIBELLES_SIGNALEMENT.get(s["type"], s["type"]) for s in signalements[:3]
    )

    # --- Recruteur proprietaire de l'offre ---
    if offre is not None and offre.recruiter_id:
        entete = "À vérifier" if graves else "Point de vigilance"
        _creer(
            offre.recruiter_id,
            "signalement_ouvert",
            f"{entete} sur la candidature de {nom} à « {intitule} » : {motifs}.",
            "/signalements",
        )

    # --- Administrateurs, pour les seules anomalies touchant le systeme ---
    critiques = [s for s in signalements if s["type"] in TYPES_CRITIQUES]
    if critiques:
        message = (
            f"Anomalie critique sur une candidature de {nom} : "
            + ", ".join(LIBELLES_SIGNALEMENT.get(s["type"], s["type"]) for s in critiques)
            + "."
        )
        for admin in _utilisateurs_du_role("admin"):
            _creer(admin.id, "signalement_critique", message, "/signalements")


def identite_a_verifier(candidature):
    """Nom divergent -> invite le candidat à corriger avant que le doute nuise.

    Le message est délibérément neutre : dans la majorité des cas l'écart
    s'explique par un changement de nom ou une translittération, et il serait
    injuste de le formuler comme un soupçon.
    """
    if candidature.candidate_id is None:
        return
    _creer(
        candidature.candidate_id,
        "identite_a_verifier",
        "Le nom figurant sur votre CV ne correspond pas exactement à celui de "
        "votre compte. Vérifiez votre profil pour éviter tout retard de "
        "traitement.",
        "/profil",
    )


def signalement_manuel(signalement, auteur=None):
    """Signalement ouvert à la main -> remonte aux administrateurs.

    Un contrôle automatique reste une observation de la machine ; un
    signalement humain engage une personne. Il a donc vocation à être connu
    de l'administration, qui pourra recouper si le même candidat est signalé
    par plusieurs recruteurs.
    """
    candidature = signalement.application
    nom = (
        candidature.candidate.full_name
        if candidature and candidature.candidate else "un candidat"
    )
    offre = candidature.offer.title if candidature and candidature.offer else "une offre"
    libelle = LIBELLES_SIGNALEMENT.get(signalement.type, signalement.type)
    par = f" par {auteur.full_name}" if auteur else ""

    message = (
        f"Signalement ouvert{par} sur la candidature de {nom} à « {offre} » : {libelle}."
    )
    for admin in _utilisateurs_du_role("admin"):
        if auteur and admin.id == auteur.id:
            continue
        _creer(admin.id, "signalement_ouvert", message, "/signalements")


def signalement_traite(signalement, auteur=None):
    """Décision prise sur un signalement -> trace auprès des administrateurs."""
    candidature = signalement.application
    nom = (
        candidature.candidate.full_name
        if candidature and candidature.candidate else "un candidat"
    )
    verdict = "confirmé" if signalement.statut == "confirme" else "écarté"
    libelle = LIBELLES_SIGNALEMENT.get(signalement.type, signalement.type)

    message = f"Signalement « {libelle} » {verdict} sur la candidature de {nom}."
    for admin in _utilisateurs_du_role("admin"):
        if auteur and admin.id == auteur.id:
            continue
        _creer(admin.id, "signalement_traite", message, "/signalements")


def compter_non_lues(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def lister(user_id, limite=20):
    return (
        Notification.query.filter_by(user_id=user_id)
        .order_by(Notification.created_at.desc())
        .limit(limite)
        .all()
    )


def marquer_lue(user_id, notification_id):
    notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if notif is None:
        return False
    notif.is_read = True
    db.session.commit()
    return True


def marquer_toutes_lues(user_id):
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()
