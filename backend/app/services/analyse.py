"""Orchestration de l'analyse complète d'une candidature (S3-08).

Enchaîne les étapes du traitement et produit un résultat unique, directement
exploitable par l'interface :

    CV (PDF)  →  extraction  →  analyse linguistique  →  profil structuré
                                        ↓
                      similarité sémantique avec l'offre
                                        ↓
                    modèle appris  →  probabilité d'adéquation
                                        ↓
                  moteur de règles + pondération  →  score expliqué

Chaque étape est traçable : le résultat indique la méthode d'extraction
employée, le profil retenu, l'avis du modèle et le détail du calcul, de sorte
qu'un recruteur puisse toujours comprendre l'origine d'une note.
"""
import logging

from ..extensions import db
from ..models.signalement import Signalement
from . import ats, extraction, fraude, observabilite, semantique
from .ml import prediction
from .scoring import calculer_score

logger = logging.getLogger(__name__)


def controler_anomalies(candidature, texte, profil_ats, chemin=None):
    """Passe la candidature au crible des contrôles et enregistre les écarts.

    Les signalements encore à l'état « nouveau » sont remplacés : une
    réanalyse doit refléter l'état courant du dossier. Ceux qu'un recruteur a
    déjà examinés sont conservés — sa décision ne doit pas être effacée par un
    traitement automatique.

    Retourne la liste brute des anomalies, que l'appelant utilise pour notifier.
    """
    trouves, empreinte = fraude.analyser(
        candidature, texte=texte, profil=profil_ats, chemin=chemin
    )
    candidature.cv_empreinte = empreinte

    if candidature.id is not None:
        Signalement.query.filter_by(
            application_id=candidature.id, statut="nouveau"
        ).delete(synchronize_session=False)

    for anomalie in trouves:
        db.session.add(
            Signalement(
                application=candidature,
                type=anomalie["type"],
                severite=anomalie["severite"],
                message=anomalie["message"],
                details=anomalie.get("details"),
            )
        )

    return trouves


def analyser_candidature(candidature, chemin_cv=None):
    """Analyse une candidature de bout en bout et met à jour son score.

    L'objet `candidature` est modifié en mémoire ; la validation en base
    reste à la charge de l'appelant, qui maîtrise la transaction.
    """
    offre = candidature.offer
    chemin = chemin_cv or candidature.cv_path

    # Chaque etape est chronometree. Le cout se repartit tres inegalement —
    # la reconnaissance optique et les plongements dominent — et seule la
    # mesure permet de savoir laquelle ralentit une analyse donnee.
    chrono = observabilite.Chronometre()

    # 1. Extraction du texte (couche native, puis OCR si necessaire)
    with chrono.etape("extraction"):
        resultat = extraction.extraire_texte(chemin)

    if not resultat.reussie:
        candidature.score = None
        candidature.score_details = {
            "statut": "extraction_echouee",
            "message": (
                resultat.erreur
                or "Le contenu du CV n'a pas pu être lu automatiquement."
            ),
            "extraction": resultat.to_dict(),
            "action_suggeree": "Saisir le profil manuellement pour obtenir un score.",
            "mesures": chrono.resultat(),
            "provenance": observabilite.provenance(),
        }
        return candidature.score_details

    # 2. Profil structure normalise (identite, experiences, formations,
    #    certifications, langues, competences)
    with chrono.etape("analyse_structurelle"):
        profil_ats = ats.analyser_cv(resultat.texte)
        profil = ats.vers_profil_scoring(profil_ats)

    # 3. Proximite semantique entre le CV et l'offre
    with chrono.etape("similarite_semantique"):
        texte_offre = semantique.texte_offre(offre)
        similarite, methode_sim = semantique.similarite(resultat.texte, texte_offre)

    # 4. Avis du modele appris (None si aucun modele n'est disponible)
    with chrono.etape("modele_appris"):
        probabilite = prediction.probabilite(
            resultat.texte, texte_offre, profil_ats=profil_ats, offre=offre
        )

    # 5. Score hybride : regles metiers, ponderation, ajustement du modele
    with chrono.etape("calcul_du_score"):
        score, details = calculer_score(
            profil,
            offre,
            similarite_semantique=similarite,
            probabilite_modele=probabilite,
        )

    # 6. Controles d'anomalies. Ils n'influent ni sur la note ni sur le statut :
    #    un signalement ouvre une verification humaine, il ne decide de rien.
    with chrono.etape("controles_anomalies"):
        anomalies = controler_anomalies(candidature, resultat.texte, profil_ats, chemin)

    details.update(
        {
            "statut": "analysee",
            "profil_analyse": profil,
            "profil_ats": profil_ats,
            "extraction": resultat.to_dict(),
            "similarite": {"valeur": round(similarite, 3), "methode": methode_sim},
            "controles": {
                "nombre": len(anomalies),
                "severite_maximale": fraude.severite_maximale(anomalies),
                "types": [a["type"] for a in anomalies],
            },
            "mesures": chrono.resultat(),
            # Avec quoi ce score a-t-il ete produit : versions du moteur, du
            # modele de plongements, du modele appris, et commit deploye.
            "provenance": observabilite.provenance(methode_sim),
        }
    )

    chrono.journaliser(f"candidature {candidature.id or 'nouvelle'}")

    candidature.score = score
    candidature.score_details = details
    return details


def analyser_texte(texte, offre):
    """Analyse un texte de CV déjà extrait, sans passer par un fichier.

    Utilisé par les tests et par les scripts d'évaluation du modèle.
    """
    profil_ats = ats.analyser_cv(texte)
    profil = ats.vers_profil_scoring(profil_ats)
    texte_offre = semantique.texte_offre(offre)
    similarite, methode = semantique.similarite(texte, texte_offre)
    probabilite = prediction.probabilite(
        texte, texte_offre, profil_ats=profil_ats, offre=offre
    )
    score, details = calculer_score(
        profil,
        offre,
        similarite_semantique=similarite,
        probabilite_modele=probabilite,
    )
    details.update(
        {
            "statut": "analysee",
            "profil_analyse": profil,
            "profil_ats": profil_ats,
            "similarite": {"valeur": round(similarite, 3), "methode": methode},
        }
    )
    return score, details
