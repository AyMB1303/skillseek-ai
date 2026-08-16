"""Orchestration de l'assistant : récupération, calcul, génération.

Un modèle de langue reformule bien mais compte mal : lui demander « combien
de candidatures ont dépassé le seuil » revient à espérer qu'il additionne
correctement des dizaines de documents. Les grandeurs chiffrées sont donc
calculées par des requêtes en base et injectées dans le contexte comme des
faits établis ; le générateur ne fait que les mettre en forme.

Cette séparation entre les faits et leur formulation est la garantie que
les chiffres affichés sont exacts, quel que soit le fournisseur employé.
"""
import re

from ...models.application import Application
from ...models.job_offer import JobOffer
from ..scoring import PLAFOND_TOP, SEUIL_RETENU
from . import administration, generation, index, redaction

SUGGESTIONS = [
    "Quels sont les meilleurs profils actuellement ?",
    "Combien de candidatures attendent une décision ?",
    "Quel est le score moyen par offre ?",
    "Pourquoi certaines candidatures sont-elles écartées ?",
    "Comment fonctionne le calcul du score ?",
]


# --------------------------------------------------------------------------
# Faits chiffrés
# --------------------------------------------------------------------------

def _candidatures(portee):
    requete = Application.query
    if portee is not None:
        offres = [o.id for o in JobOffer.query.filter_by(recruiter_id=portee).all()]
        if not offres:
            return []
        requete = requete.filter(Application.offer_id.in_(offres))
    return requete.all()


def _offres(portee):
    requete = JobOffer.query.filter(JobOffer.deleted_at.is_(None))
    if portee is not None:
        requete = requete.filter_by(recruiter_id=portee)
    return requete.all()


def faits(portee=None):
    """Grandeurs de référence, calculées et non déduites."""
    candidatures = _candidatures(portee)
    offres = _offres(portee)
    notes = [c.score for c in candidatures if c.score is not None]

    retenues = [c for c in candidatures if (c.score or 0) >= SEUIL_RETENU]
    entretiens = [c for c in candidatures if c.status == "interview"]
    recrutes = [c for c in candidatures if c.status == "hired"]
    attente = [c for c in candidatures if c.status in ("received", "under_review")]

    return {
        "offres_total": len(offres),
        "offres_ouvertes": len([o for o in offres if o.status == "open"]),
        "candidatures_total": len(candidatures),
        "candidatures_analysees": len(notes),
        "candidatures_sans_note": len(candidatures) - len(notes),
        "au_dessus_du_seuil": len(retenues),
        "entretiens": len(entretiens),
        "recrutes": len(recrutes),
        "en_attente_de_decision": len(attente),
        "note_moyenne": round(sum(notes) / len(notes)) if notes else None,
        "note_maximale": max(notes) if notes else None,
        "note_minimale": min(notes) if notes else None,
    }


def _texte_faits(f):
    lignes = [
        "FAITS VÉRIFIÉS (chiffres calculés sur la base de données) :",
        f"- Offres : {f['offres_total']} au total, dont {f['offres_ouvertes']} ouvertes.",
        f"- Candidatures reçues : {f['candidatures_total']}.",
        f"- Candidatures analysées : {f['candidatures_analysees']} "
        f"(dont {f['candidatures_sans_note']} sans note faute de CV lisible).",
        f"- Au-dessus du seuil de {SEUIL_RETENU} : {f['au_dessus_du_seuil']}.",
        f"- En entretien : {f['entretiens']}. Recrutés : {f['recrutes']}.",
        f"- En attente d'une décision du recruteur : {f['en_attente_de_decision']}.",
    ]
    if f["note_moyenne"] is not None:
        lignes.append(
            f"- Notes : moyenne {f['note_moyenne']}, maximum {f['note_maximale']}, "
            f"minimum {f['note_minimale']} (sur 100)."
        )
    return "\n".join(lignes)


# --------------------------------------------------------------------------
# Tableaux joints à la réponse
# --------------------------------------------------------------------------

LIBELLE_STATUT = {
    "received": "Reçue", "under_review": "En étude", "shortlisted": "Présélectionné",
    "interview": "Entretien", "hired": "Recruté", "rejected": "Non retenu",
}


def _tableau_associe(question, portee):
    """Joint un tableau lorsque la question porte sur une liste ou une comparaison.

    Le tableau provient des données, jamais du texte généré : c'est lui qui
    fait foi si le lecteur veut vérifier.
    """
    q = question.lower()
    candidatures = _candidatures(portee)

    if re.search(r"meilleur|top|classement|shortlist|préséle|presele", q):
        tries = sorted(
            [c for c in candidatures if (c.score or 0) >= SEUIL_RETENU],
            key=lambda c: c.score, reverse=True,
        )[:PLAFOND_TOP]
        if tries:
            return {
                "colonnes": ["Candidat", "Offre", "Score", "Statut"],
                "lignes": [
                    [
                        c.candidate.full_name if c.candidate else "—",
                        c.offer.title if c.offer else "—",
                        f"{round(c.score)}/100",
                        LIBELLE_STATUT.get(c.status, c.status),
                    ]
                    for c in tries
                ],
            }

    if re.search(r"attente|à traiter|a traiter|décision|decision|action", q):
        attente = [c for c in candidatures if c.status in ("received", "under_review")]
        attente.sort(key=lambda c: c.score or 0, reverse=True)
        if attente:
            return {
                "colonnes": ["Candidat", "Offre", "Score"],
                "lignes": [
                    [
                        c.candidate.full_name if c.candidate else "—",
                        c.offer.title if c.offer else "—",
                        f"{round(c.score)}/100" if c.score is not None else "non analysé",
                    ]
                    for c in attente[:10]
                ],
            }

    if re.search(r"par offre|compar|chaque offre|offres", q):
        offres = _offres(portee)
        if offres:
            lignes = []
            for offre in offres:
                liste = [c for c in candidatures if c.offer_id == offre.id]
                notes = [c.score for c in liste if c.score is not None]
                lignes.append([
                    offre.title,
                    len(liste),
                    f"{round(sum(notes) / len(notes))}/100" if notes else "—",
                    len([c for c in liste if c.status == "interview"]),
                ])
            return {
                "colonnes": ["Offre", "Candidatures", "Score moyen", "Entretiens"],
                "lignes": lignes,
            }

    if re.search(r"écart|ecart|rejet|refus|seuil", q):
        ecartees = [
            c for c in candidatures if c.score is not None and c.score < SEUIL_RETENU
        ]
        if ecartees:
            lignes = []
            for c in sorted(ecartees, key=lambda x: x.score, reverse=True)[:10]:
                motifs = (c.score_details or {}).get("eliminatoires") or []
                lignes.append([
                    c.candidate.full_name if c.candidate else "—",
                    c.offer.title if c.offer else "—",
                    f"{round(c.score)}/100",
                    motifs[0] if motifs else "Score insuffisant",
                ])
            return {
                "colonnes": ["Candidat", "Offre", "Score", "Motif principal"],
                "lignes": lignes,
            }

    if re.search(r"entonnoir|funnel|conversion|pipeline", q):
        f = faits(portee)
        taux = lambda a, b: f"{round(a / b * 100)}%" if b else "—"  # noqa: E731
        return {
            "colonnes": ["Étape", "Volume", "Conversion"],
            "lignes": [
                ["Candidatures reçues", f["candidatures_total"], "100%"],
                ["Au-dessus du seuil", f["au_dessus_du_seuil"],
                 taux(f["au_dessus_du_seuil"], f["candidatures_total"])],
                ["Entretiens", f["entretiens"],
                 taux(f["entretiens"], f["au_dessus_du_seuil"])],
                ["Recrutements", f["recrutes"], taux(f["recrutes"], f["entretiens"])],
            ],
        }

    return None


def _lien_associe(documents):
    """Renvoie l'écran le plus pertinent parmi les sources retrouvées."""
    for doc in documents:
        if doc.lien and doc.type in ("candidature", "offre"):
            return {"href": doc.lien, "libelle": "Consulter l'écran concerné"}
    for doc in documents:
        if doc.lien:
            return {"href": doc.lien, "libelle": "En savoir plus"}
    return None


# --------------------------------------------------------------------------
# Point d'entrée
# --------------------------------------------------------------------------

def _repondre_administration(question, historique=None):
    """Répond dans le domaine de la gouvernance : comptes, droits, contrôles.

    Même orchestration que pour le recrutement — faits calculés, documents
    retrouvés, formulation — mais sur une base de connaissance disjointe. Voir
    le module `administration` pour la raison de fond : l'administrateur ne
    détient pas `view_applications`, et l'assistant ne doit pas le contourner.
    """
    donnees = administration.faits()

    nom_intention = administration.intention(question)
    if (nom_intention in administration.SOCIALES
            and generation.fournisseur_actif() == "gabarits"):
        return {
            "texte": administration.composer(question, [], donnees),
            "sources": [],
            "suggestions": administration.relances(question),
            "fournisseur": "conversation",
            "recherche": index.methode_active(),
            "domaine": "administration",
        }

    trouves = index.rechercher(question, None, domaine="administration")
    documents = [doc for doc, _ in trouves]

    texte, fournisseur = generation.generer(
        question, documents, administration.texte_faits(donnees),
        faits=donnees, historique=historique,
        consigne=generation.CONSIGNE_ADMINISTRATION,
        redacteur=administration.composer,
    )

    return {
        "texte": texte,
        "tableau": administration.tableau(question),
        "lien": administration.lien(question),
        "sources": [
            {**doc.to_dict(), "pertinence": round(score, 3)} for doc, score in trouves[:4]
        ],
        "suggestions": administration.relances(question),
        "fournisseur": fournisseur,
        "recherche": index.methode_active(),
        "domaine": "administration",
    }


def repondre(question, portee=None, historique=None, domaine="recrutement"):
    """Répond à une question en s'appuyant sur les données de la plateforme.

    `historique` porte les derniers tours de parole. Il n'est exploité que par
    les fournisseurs conversationnels : la rédaction déterministe traite chaque
    question isolément, faute de pouvoir interpréter une reprise implicite.

    `domaine` choisit la base de connaissance : « recrutement » pour un
    recruteur, « administration » pour un administrateur.
    """
    question = (question or "").strip()
    if not question:
        return {"texte": "Posez-moi une question sur vos recrutements.", "sources": []}

    if domaine == "administration":
        return _repondre_administration(question, historique)

    donnees = faits(portee)

    # Un echange de civilite n'appelle ni recherche documentaire ni modele de
    # langue : y repondre directement evite de renvoyer une fiche d'aide sans
    # rapport a un simple « bonjour ».
    nom_intention = redaction.intention(question)
    if nom_intention in redaction.SOCIALES and generation.fournisseur_actif() == "gabarits":
        return {
            "texte": redaction.composer(question, [], donnees),
            "sources": [],
            "suggestions": redaction.relances(question),
            "fournisseur": "conversation",
            "recherche": index.methode_active(),
        }

    trouves = index.rechercher(question, portee)
    documents = [doc for doc, _ in trouves]

    if donnees["candidatures_total"] == 0 and donnees["offres_total"] == 0:
        return {
            "texte": (
                "Aucune donnée n'est encore disponible. Publiez une offre et recevez "
                "des candidatures pour que je puisse vous répondre."
            ),
            "sources": [],
            "suggestions": ["Comment la note est-elle calculée ?",
                            "Comment le CV est-il analysé ?"],
            "fournisseur": "gabarits",
        }

    texte, fournisseur = generation.generer(
        question, documents, _texte_faits(donnees),
        faits=donnees, historique=historique,
    )

    return {
        "texte": texte,
        "tableau": _tableau_associe(question, portee),
        "lien": _lien_associe(documents),
        "sources": [
            {**doc.to_dict(), "pertinence": round(score, 3)} for doc, score in trouves[:4]
        ],
        "suggestions": redaction.relances(question),
        "fournisseur": fournisseur,
        "recherche": index.methode_active(),
        "domaine": "recrutement",
    }


def diagnostic(portee=None, domaine="recrutement"):
    """État du dispositif, affiché dans l'interface pour la transparence."""
    documents, _ = index.obtenir(portee, domaine)
    return {
        "documents_indexes": len(documents),
        "methode_recherche": index.methode_active(),
        "fournisseur_generation": generation.fournisseur_actif(),
        "suggestions": (
            administration.SUGGESTIONS if domaine == "administration" else SUGGESTIONS
        ),
        "domaine": domaine,
    }
