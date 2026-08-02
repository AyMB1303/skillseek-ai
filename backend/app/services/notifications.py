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


def offre_publiee(offre):
    """Publication d'une offre -> notifie les administrateurs (suivi d'activité)."""
    auteur = offre.recruiter.full_name if offre.recruiter else "un recruteur"
    message = f"{auteur} a publié l'offre « {offre.title} »."
    for admin in _utilisateurs_du_role("admin"):
        _creer(admin.id, "offre_publiee", message, "/admin/utilisateurs")


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
