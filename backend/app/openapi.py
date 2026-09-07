"""Description OpenAPI de l'API, **dérivée de l'application elle-même**.

Le choix qui gouverne ce fichier : ne rien écrire à la main de ce que le code
sait déjà. Une spécification tenue dans un fichier séparé décrit l'API au jour
où on l'a rédigée ; six semaines plus tard elle décrit une API qui n'existe
plus, et le lecteur ne peut pas savoir laquelle des deux ment. Ici la
description est reconstruite à chaque appel à partir de trois sources vivantes :

* la **table de routage** de Flask — chemins réels, méthodes réelles,
  paramètres réels, y compris leur type ;
* la **docstring** de chaque vue, qui porte déjà l'intention de la route ;
* les **décorateurs de contrôle d'accès**, qui inscrivent sur la fonction les
  permissions qu'ils exigent (voir « middleware/permissions.py »).

La conséquence est la propriété qui compte : **la section « sécurité » de la
documentation n'est pas une déclaration, c'est un relevé.** Elle ne dit pas
quelle permission une route *devrait* demander, elle dit celle que le
décorateur *demande*. Une route ajoutée demain sans garde apparaîtra publique,
et se verra.

Ce module n'ajoute aucune dépendance : la structure produite est un simple
dictionnaire conforme à OpenAPI 3.0.3, que n'importe quel outil sait lire.
"""
from __future__ import annotations

import re

from flask import Blueprint, current_app, jsonify

VERSION_API = "1.0.0"

# Méthodes ajoutées d'office par Werkzeug : les décrire n'apprendrait rien.
METHODES_IMPLICITES = {"HEAD", "OPTIONS"}

# Seuls les fichiers servis par Flask sont écartés : ils ne constituent pas
# une API. Les deux routes de ce module figurent au contrat comme les autres —
# un document qui dissimulerait ses propres routes serait précisément le genre
# d'inexactitude discrète que cette construction cherche à rendre impossible.
ENDPOINTS_EXCLUS = {"static"}

# Correspondance entre les convertisseurs d'URL de Werkzeug et les types
# OpenAPI. Les clés sont les noms de classe privés du nom « Converter », en
# minuscules : « IntegerConverter » donne « integer ». Un premier essai
# indexait sur le préfixe écrit dans la route — « <int:…> » — mais ce préfixe
# n'existe nulle part dans l'objet ; tous les paramètres sortaient en texte,
# sans qu'aucune erreur ne le signale.
TYPES = {
    "integer": {"type": "integer", "format": "int64"},
    "float": {"type": "number"},
    "unicode": {"type": "string"},
    "path": {"type": "string"},
    "uuid": {"type": "string", "format": "uuid"},
    "any": {"type": "string"},
}

# Intitulés lisibles pour les groupes de routes. La clé est le nom du
# blueprint ; une route dont le blueprint n'y figure pas garde son nom brut,
# ce qui la rend visible plutôt que de la ranger silencieusement ailleurs.
GROUPES = {
    "auth": "Authentification",
    "users": "Utilisateurs et droits",
    "offers": "Offres d'emploi",
    "applications": "Candidatures et analyse",
    "evaluations": "Évaluations après entretien",
    "dashboard": "Tableaux de bord",
    "profile": "Profil du candidat",
    "notifications": "Notifications",
    "assistant": "Assistant documentaire",
    "signalements": "Contrôle de sincérité",
    "journal": "Journal d'audit",
}

openapi_bp = Blueprint("openapi", __name__)


def chemin_openapi(regle: str) -> str:
    """Traduit « /api/offers/<int:offer_id> » en « /api/offers/{offer_id} ».

    Exposée plutôt que gardée pour ce module : les tests s'en servent pour
    retrouver, dans le document, l'entrée correspondant à une règle de
    routage. Sans elle, ils réimplémenteraient la même conversion, et une
    divergence entre les deux ferait échouer des tests pour une raison sans
    rapport avec ce qu'ils vérifient.
    """
    return re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", regle)


def _resume_et_description(vue) -> tuple[str, str]:
    """Sépare la première phrase de la docstring du reste.

    Les vues de ce projet portent des docstrings rédigées : la première ligne
    énonce ce que fait la route, les suivantes expliquent pourquoi. C'est
    exactement la distinction qu'OpenAPI fait entre « summary » et
    « description », donc on ne réécrit rien.
    """
    # La vue est enveloppée par les décorateurs de contrôle d'accès, qui
    # emploient « functools.wraps » : la docstring d'origine est donc bien
    # celle que l'on lit ici.
    doc = (vue.__doc__ or "").strip()
    if not doc:
        return "", ""
    morceaux = doc.split("\n\n", 1)
    resume = " ".join(morceaux[0].split())
    if len(morceaux) == 1:
        return resume, ""
    # Chaque paragraphe est réduit à une ligne : la coupure des lignes et
    # l'indentation d'une docstring servent au lecteur du code, pas au rendu.
    # Les conserver produisait des trous de plusieurs espaces au milieu des
    # phrases. Les paragraphes, eux, sont préservés — ce sont eux qui portent
    # la structure du propos.
    paragraphes = [
        " ".join(bloc.split())
        for bloc in morceaux[1].split("\n\n")
        if bloc.strip()
    ]
    return resume, "\n\n".join(paragraphes)


def _parametres(regle) -> list[dict]:
    """Extrait les paramètres de chemin depuis la règle de routage.

    Leur type vient du convertisseur employé dans la route — « <int:offer_id> »
    donne un entier — donc il ne peut pas contredire ce que le service accepte.
    """
    parametres = []
    for nom, convertisseur in regle._converters.items():
        cle = type(convertisseur).__name__.replace("Converter", "").lower()
        parametres.append(
            {
                "name": nom,
                "in": "path",
                "required": True,
                "schema": TYPES.get(cle, {"type": "string"}),
            }
        )
    return parametres


def _reponses(protegee: bool, a_parametre: bool) -> dict:
    """Réponses communes à toutes les routes.

    Ce ne sont pas des suppositions : ce sont les codes que les décorateurs et
    « get_or_404 » produisent réellement. Les corps de réponse propres à chaque
    route ne sont pas décrits — les inventer serait pire que de les omettre.
    """
    reponses = {"200": {"description": "Succès."}}
    if protegee:
        reponses["401"] = {
            "description": "Jeton absent, expiré, révoqué, ou compte désactivé."
        }
        reponses["403"] = {
            "description": (
                "Permission refusée, ou ressource n'appartenant pas à "
                "l'utilisateur. Le corps nomme la permission manquante."
            )
        }
    if a_parametre:
        reponses["404"] = {"description": "Ressource inexistante."}
    return reponses


def construire(app) -> dict:
    """Assemble le document OpenAPI à partir de l'application donnée."""
    chemins: dict[str, dict] = {}
    publiques: list[str] = []

    for regle in sorted(app.url_map.iter_rules(), key=lambda r: str(r.rule)):
        if regle.endpoint in ENDPOINTS_EXCLUS or regle.rule.startswith("/static"):
            continue

        vue = app.view_functions[regle.endpoint]
        protegee = getattr(vue, "__authentification_requise__", False)
        permissions = getattr(vue, "__permissions_requises__", ())
        resume, description = _resume_et_description(vue)
        groupe = regle.endpoint.split(".")[0]

        chemin = chemin_openapi(regle.rule)
        entree = chemins.setdefault(chemin, {})

        for methode in sorted(regle.methods - METHODES_IMPLICITES):
            if not protegee:
                publiques.append(f"{methode} {chemin}")

            operation = {
                "operationId": f"{regle.endpoint}_{methode.lower()}",
                "tags": [GROUPES.get(groupe, groupe)],
                "summary": resume or f"{methode} {chemin}",
                "responses": _reponses(protegee, bool(regle.arguments)),
            }
            if description:
                operation["description"] = description
            if regle.arguments:
                operation["parameters"] = _parametres(regle)
            if protegee:
                operation["security"] = [{"jetonPorteur": []}]
                if permissions:
                    # Extension propre au projet : OpenAPI sait exprimer
                    # « il faut un jeton », pas « il faut la permission
                    # manage_users ». Le champ est relevé du décorateur, donc
                    # exact par construction.
                    operation["x-permissions-requises"] = list(permissions)
            entree[methode.lower()] = operation

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "SkillSeek AI — API de présélection explicable",
            "version": VERSION_API,
            "description": (
                "Contrat de l'API du service applicatif.\n\n"
                "**Ce document est produit par l'application, à l'exécution.** "
                "Les chemins, les méthodes et les types de paramètres sont lus "
                "dans la table de routage ; les permissions exigées sont "
                "relevées sur les décorateurs qui les appliquent. Il ne peut "
                "donc pas décrire une API différente de celle qui tourne.\n\n"
                "Deux points d'entrée seulement sont ouverts sans jeton : "
                "l'inscription et la sonde d'état. Tous les autres exigent un "
                "jeton porteur, et la plupart une permission nommée, relue en "
                "base à chaque appel — retirer un droit prend effet "
                "immédiatement, sans attendre l'expiration des sessions "
                "ouvertes (règle RG-02)."
            ),
        },
        "servers": [{"url": "/", "description": "Service applicatif"}],
        "tags": [
            {"name": intitule}
            for intitule in dict.fromkeys(GROUPES.values())
        ],
        "components": {
            "securitySchemes": {
                "jetonPorteur": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": (
                        "Jeton obtenu par « POST /api/auth/login ». Il ne "
                        "porte que l'identité : les droits ne sont jamais "
                        "recopiés dedans."
                    ),
                }
            }
        },
        "paths": chemins,
        # Relevé, pas déclaré : la liste est celle des routes que le code
        # laisse effectivement sans garde. Elle est publiée pour qu'un écart
        # se voie — c'est l'audit du chapitre sur le cloisonnement, rendu
        # consultable.
        "x-routes-publiques": sorted(publiques),
    }


@openapi_bp.get("/openapi.json")
def document():
    """Contrat de l'API, au format OpenAPI 3.0.3."""
    return jsonify(construire(current_app))


@openapi_bp.get("/docs")
def page():
    """Documentation navigable de l'API."""
    # Deux décisions se logent ici.
    #
    # L'interface de lecture est chargée depuis un réseau de diffusion : c'est
    # une commodité de consultation, volontairement séparée du contrat.
    # Celui-ci est servi en JSON par la route ci-dessus et reste exploitable
    # sans aucun accès extérieur — un outil hors ligne, une génération de
    # client, une vérification en intégration continue.
    #
    # Le contrat est ouvert sans jeton, contrairement à la page d'indicateurs
    # qui, elle, ne l'est pas. La distinction n'est pas arbitraire : les
    # indicateurs renseignent sur le trafic réel — volumes, heures creuses,
    # taux d'erreur — quand le contrat ne décrit qu'une structure, sans livrer
    # une seule donnée. Publier le modèle d'accès permet de le vérifier de
    # l'extérieur ; le dissimuler ne protégerait rien qu'une énumération de
    # routes ne retrouverait.
    return """<!DOCTYPE html>
<html lang="fr">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SkillSeek AI — API</title>
    <link rel="stylesheet"
          href="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui.min.css" />
  </head>
  <body>
    <div id="swagger"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/5.17.14/swagger-ui-bundle.min.js"></script>
    <script>
      window.onload = () => SwaggerUIBundle({
        url: "/api/openapi.json",
        dom_id: "#swagger",
        deepLinking: true,
        docExpansion: "none",
      });
    </script>
  </body>
</html>"""
