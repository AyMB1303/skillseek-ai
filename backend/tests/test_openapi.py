"""Le contrat d'API décrit-il l'application qui tourne ?

Une documentation d'API se dégrade en silence : elle continue de s'afficher,
correctement formatée, en décrivant une version qui n'existe plus. Ces tests
portent donc moins sur la forme du document que sur son **accord avec le
code** — et le seul écart qui compte vraiment est celui de la sécurité, une
route annoncée protégée mais ouverte n'étant pas une erreur de documentation
mais une fausse assurance.
"""
import json

from app.openapi import ENDPOINTS_EXCLUS, chemin_openapi, construire


def _regles_decrites(app):
    return [
        regle
        for regle in app.url_map.iter_rules()
        if regle.endpoint not in ENDPOINTS_EXCLUS
        and not regle.rule.startswith("/static")
    ]


# ------------------------------ Structure --------------------------------


def test_le_document_est_servi_et_bien_forme(client):
    reponse = client.get("/api/openapi.json")
    assert reponse.status_code == 200
    doc = json.loads(reponse.data)
    assert doc["openapi"].startswith("3.0")
    assert doc["info"]["title"] and doc["info"]["version"]
    assert doc["paths"]


def test_aucune_route_n_echappe_au_contrat(app):
    """Toute route exposée figure au document.

    C'est la propriété qui distingue un document produit d'un document
    rédigé : l'oubli y est impossible, puisque la source est la table de
    routage elle-même. Le test garde la porte fermée si quelqu'un venait à
    remplacer cette construction par une liste écrite à la main.
    """
    doc = construire(app)
    manquantes = [
        regle.rule
        for regle in _regles_decrites(app)
        if chemin_openapi(regle.rule) not in doc["paths"]
    ]
    assert not manquantes, f"routes absentes du contrat : {manquantes}"


def test_chaque_methode_exposee_est_decrite(app):
    """Une route peut répondre à plusieurs verbes ; chacun doit être décrit."""
    doc = construire(app)
    oublis = []
    for regle in _regles_decrites(app):
        decrites = set(doc["paths"][chemin_openapi(regle.rule)])
        for methode in regle.methods - {"HEAD", "OPTIONS"}:
            if methode.lower() not in decrites:
                oublis.append(f"{methode} {regle.rule}")
    assert not oublis, f"méthodes non décrites : {oublis}"


# ------------------------------- Sécurité ---------------------------------


def test_le_contrat_annonce_une_protection_exactement_ou_le_code_en_applique(app):
    """L'accord entre ce qui est dit et ce qui est fait.

    C'est le test central de ce fichier. Une route annoncée protégée mais
    laissée ouverte donne une assurance fausse, ce qui est pire que pas
    d'assurance du tout : personne ne va vérifier ce qui est écrit noir sur
    blanc.
    """
    doc = construire(app)
    ecarts = []
    for regle in _regles_decrites(app):
        vue = app.view_functions[regle.endpoint]
        protegee = getattr(vue, "__authentification_requise__", False)
        operations = doc["paths"][chemin_openapi(regle.rule)]
        # On ne parcourt que les méthodes de *cette* règle : un même chemin
        # peut héberger plusieurs vues — un GET et un DELETE portés par des
        # fonctions différentes, aux droits différents. Comparer toutes les
        # opérations du chemin à une seule vue reviendrait à confondre deux
        # routes qui n'ont en commun que leur adresse.
        for methode in regle.methods - {"HEAD", "OPTIONS"}:
            operation = operations[methode.lower()]
            if ("security" in operation) != protegee:
                ecarts.append(f"{methode} {regle.rule}")
    assert not ecarts, f"le contrat et le code divergent sur : {ecarts}"


def test_les_permissions_publiees_sont_relevees_sur_le_decorateur(app):
    """Les codes annoncés sont ceux que la garde exige, sans recopie."""
    doc = construire(app)
    releves = 0
    for regle in _regles_decrites(app):
        vue = app.view_functions[regle.endpoint]
        attendues = list(getattr(vue, "__permissions_requises__", ()))
        operations = doc["paths"][chemin_openapi(regle.rule)]
        # Là encore, uniquement les méthodes de cette règle : un chemin peut
        # servir deux vues aux permissions distinctes.
        for methode in regle.methods - {"HEAD", "OPTIONS"}:
            operation = operations[methode.lower()]
            assert operation.get("x-permissions-requises", []) == attendues, (
                f"{methode} {regle.rule}"
            )
            releves += bool(attendues)
    assert releves > 0, "aucune permission relevée : le mécanisme ne marche pas"


def test_le_releve_des_routes_ouvertes_ne_contient_que_l_attendu(app):
    """L'audit d'accès, rendu consultable.

    Le test échoue dès qu'une route est ajoutée sans garde — l'oubli le plus
    silencieux qui soit, puisqu'une route ouverte fonctionne parfaitement.
    """
    doc = construire(app)
    autorisees = {
        "/api/auth/register",   # inscription : il faut bien un premier accès
        "/api/auth/login",      # échange des identifiants contre un jeton
        "/api/health",          # sonde d'état
        "/api/ready",           # sonde de disponibilité
        "/metrics",             # lue par le collecteur, non routée à l'entrée
        "/api/openapi.json",    # contrat : une structure, aucune donnée
        "/api/docs",
    }
    inattendues = [
        entree
        for entree in doc["x-routes-publiques"]
        if entree.split(" ", 1)[1] not in autorisees
    ]
    assert not inattendues, f"routes ouvertes non prévues : {inattendues}"


# ------------------------------- Contenu ----------------------------------


def test_les_resumes_viennent_des_docstrings(app):
    """Une route documentée dans le code l'est dans le contrat.

    Le point n'est pas cosmétique : il évite d'entretenir deux textes qui
    disent la même chose et finissent par ne plus le dire pareil.
    """
    doc = construire(app)
    rediges = [
        operation
        for chemin in doc["paths"].values()
        for operation in chemin.values()
        if not operation["summary"].startswith(
            ("GET ", "POST ", "PUT ", "PATCH ", "DELETE ")
        )
    ]
    assert len(rediges) >= 30, (
        f"seulement {len(rediges)} routes portent un résumé rédigé"
    )


def test_un_parametre_entier_est_decrit_comme_un_entier(app):
    """« <int:offer_id> » ne doit pas se décrire comme du texte.

    Le premier essai indexait la table des types sur le préfixe écrit dans la
    route, qui n'existe pas dans l'objet de Werkzeug : tous les paramètres
    sortaient en texte, sans qu'aucune erreur ne le signale.
    """
    doc = construire(app)
    entiers = [
        parametre
        for chemin in doc["paths"].values()
        for operation in chemin.values()
        for parametre in operation.get("parameters", [])
        if parametre["schema"].get("type") == "integer"
    ]
    assert entiers, "aucun paramètre entier détecté dans le contrat"


def test_un_paragraphe_de_docstring_ne_garde_pas_son_indentation(app):
    """Les blancs d'indentation ne doivent pas se retrouver dans le rendu."""
    doc = construire(app)
    for chemin in doc["paths"].values():
        for operation in chemin.values():
            description = operation.get("description", "")
            assert "  " not in description, (
                f"indentation conservée dans « {operation['operationId']} »"
            )


def test_la_page_de_documentation_repond(client):
    reponse = client.get("/api/docs")
    assert reponse.status_code == 200
    assert b"/api/openapi.json" in reponse.data
