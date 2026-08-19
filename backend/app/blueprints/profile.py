"""Profil utilisateur : modification, mot de passe, droits RGPD / loi 09-08."""
import re

from flask import Blueprint, jsonify, request

from ..extensions import db
from ..middleware.permissions import current_user_required
from ..models.application import Application

profile_bp = Blueprint("profile", __name__)

PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


@profile_bp.patch("")
@current_user_required
def modifier(current_user):
    data = request.get_json(silent=True) or {}
    nom = (data.get("full_name") or "").strip()
    if len(nom) < 3:
        return jsonify(errors={"full_name": "Nom complet requis (3 caractères minimum)."}), 400
    current_user.full_name = nom
    db.session.commit()
    return jsonify(user=current_user.to_dict())


@profile_bp.post("/password")
@current_user_required
def changer_mot_de_passe(current_user):
    data = request.get_json(silent=True) or {}
    actuel = data.get("current_password") or ""
    nouveau = data.get("new_password") or ""

    if not current_user.check_password(actuel):
        return jsonify(errors={"current_password": "Mot de passe actuel incorrect."}), 400
    if not PASSWORD_RE.match(nouveau):
        return jsonify(
            errors={"new_password": "8 caractères minimum, avec majuscule, minuscule et chiffre."}
        ), 400

    current_user.set_password(nouveau)
    db.session.commit()
    return jsonify(message="Mot de passe modifié.")


@profile_bp.get("/competences")
@current_user_required
def lire_profil_declare(current_user):
    """Profil déclaré, et ce que la plateforme sait déjà par ailleurs."""
    from ..services.orientation import profil_du_candidat

    profil, origine = profil_du_candidat(current_user)
    return jsonify(
        declare=current_user.profil_declare,
        profil_retenu=profil,
        origine=origine,
    )


@profile_bp.put("/competences")
@current_user_required
def enregistrer_profil_declare(current_user):
    """Enregistre le profil déclaré par le candidat.

    Les compétences passent par le référentiel du moteur : « JS » devient
    « javascript », « Postgres » devient « postgresql ». Sans cette
    normalisation, une saisie libre produirait des recommandations vides sans
    que la personne comprenne pourquoi.

    Rien n'est obligatoire, et rien n'est vérifié. Ce profil sert à orienter
    quelqu'un dans un catalogue d'offres, jamais à décider de son sort — c'est
    ce qui rend une déclaration acceptable ici, alors qu'elle ne le serait pas
    dans une candidature.
    """
    from ..services.competences import canoniser

    donnees = request.get_json(silent=True) or {}

    brutes = donnees.get("skills") or []
    if not isinstance(brutes, list):
        return jsonify(errors={"skills": "Liste de compétences attendue."}), 400
    if len(brutes) > 40:
        return jsonify(errors={"skills": "Quarante compétences au maximum."}), 400

    competences = []
    for brute in brutes:
        valeur = canoniser(str(brute))
        if valeur and valeur not in competences:
            competences.append(valeur)

    try:
        experience = int(donnees.get("experience_years") or 0)
    except (TypeError, ValueError):
        return jsonify(errors={"experience_years": "Nombre d'années attendu."}), 400
    if not 0 <= experience <= 60:
        return jsonify(errors={"experience_years": "Valeur invraisemblable."}), 400

    diplome = (donnees.get("degree") or "").strip().lower() or None

    current_user.profil_declare = {
        "skills": competences,
        "experience_years": experience,
        "degree": diplome,
        "ville": (donnees.get("ville") or "").strip() or None,
        "contrat": (donnees.get("contrat") or "").strip() or None,
    }
    db.session.commit()
    return jsonify(profil=current_user.profil_declare)


@profile_bp.get("/recommandations")
@current_user_required
def recommandations(current_user):
    """Offres classées selon le profil connu du candidat."""
    from ..services.orientation import recommander

    profil = current_user.profil_declare or {}
    return jsonify(
        recommander(
            current_user,
            ville=request.args.get("ville", profil.get("ville")),
            contrat=request.args.get("contrat", profil.get("contrat")),
        )
    )


@profile_bp.get("/data")
@current_user_required
def exporter_donnees(current_user):
    """Droit d'accès : export des données personnelles de l'utilisateur."""
    candidatures = Application.query.filter_by(candidate_id=current_user.id).all()
    return jsonify(
        compte=current_user.to_dict(),
        candidatures=[
            {
                "offre": c.offer.title if c.offer else None,
                "statut": c.status,
                "score": c.score,
                "deposee_le": c.created_at.isoformat(),
            }
            for c in candidatures
        ],
    )


@profile_bp.delete("")
@current_user_required
def supprimer_compte(current_user):
    """Droit à l'effacement : supprime le compte et ses candidatures."""
    if current_user.role and current_user.role.name == "admin":
        return jsonify(error="Un administrateur ne peut pas supprimer son propre compte."), 400

    Application.query.filter_by(candidate_id=current_user.id).delete()
    db.session.delete(current_user)
    db.session.commit()
    return jsonify(message="Compte supprimé.")
