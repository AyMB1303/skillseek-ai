"""Exposition des indicateurs d'exploitation.

Ces tests portent sur une propriété qui se casse en silence. Un indicateur mal
étiqueté continue de s'exposer, le tableau de bord continue de s'afficher, et
personne ne remarque rien avant le jour où l'on cherche à comprendre une
panne. Ils vérifient donc surtout ce qui ne doit *pas* arriver.
"""
from app import supervision

from .conftest import auth_header


def _lire(client) -> str:
    reponse = client.get("/metrics")
    assert reponse.status_code == 200
    return reponse.data.decode()


# --------------------------- Indicateurs techniques ------------------------

def test_la_page_expose_le_format_attendu(client):
    corps = _lire(client)
    # Le format texte de Prometheus commente chaque famille avant de la
    # publier ; son absence signalerait un registre vide.
    assert "# HELP skillseek_requetes_total" in corps
    assert "# TYPE skillseek_duree_requete_secondes histogram" in corps


def test_une_requete_est_comptee_avec_son_code(client):
    client.get("/api/health")
    client.get("/api/offers")
    corps = _lire(client)
    assert 'skillseek_requetes_total{code="200"' in corps


def test_les_identifiants_ne_creent_pas_une_serie_chacun(client, admin_token):
    """La règle de routage sert d'étiquette, jamais le chemin appelé.

    C'est la faute classique de ce type d'instrumentation : étiqueter avec
    « /api/offers/1 » puis « /api/offers/2 » fait croître le nombre de séries
    avec les données, jusqu'à saturer le collecteur. Le test échouerait si
    quelqu'un remplaçait `url_rule` par `request.path`.
    """
    for identifiant in (1, 2, 3):
        client.get(f"/api/offers/{identifiant}", headers=auth_header(admin_token))
    corps = _lire(client)
    assert "/api/offers/1" not in corps
    assert "/api/offers/2" not in corps


def test_une_route_inexistante_est_rangee_sous_inconnue(client):
    """Un balayage automatisé ne doit pas pouvoir créer autant de séries
    qu'il tente d'URL."""
    client.get("/chemin-qui-nexiste-pas")
    client.get("/autre-chemin-invente")
    corps = _lire(client)
    assert 'route="inconnue"' in corps
    assert "chemin-qui-nexiste-pas" not in corps


# ----------------------------- Indicateurs métier --------------------------

def test_une_analyse_aboutie_est_distinguee_dune_analyse_en_echec(client):
    supervision.observer_analyse(2.0, 72, aboutie=True)
    supervision.observer_analyse(0.2, None, aboutie=False)
    corps = _lire(client)
    assert 'skillseek_analyses_total{resultat="aboutie"}' in corps
    assert 'skillseek_analyses_total{resultat="indisponible"}' in corps


def test_une_analyse_en_echec_ne_produit_aucune_note(client):
    """Une note absente ne doit pas être comptée comme un zéro : elle
    tirerait la distribution vers le bas et laisserait croire à une
    dégradation du moteur là où il n'a simplement pas tourné."""
    avant = supervision.NOTES._sum.get()
    supervision.observer_analyse(0.1, None, aboutie=False)
    assert supervision.NOTES._sum.get() == avant


def test_le_seuil_de_preselection_est_une_borne_de_histogramme(client):
    """La part des candidatures écartées doit se lire directement, sans
    interpolation entre deux seaux."""
    supervision.observer_analyse(1.0, 45, aboutie=True)
    corps = _lire(client)
    assert 'skillseek_note_produite_bucket{le="50.0"}' in corps


def test_la_sonde_de_disponibilite_publie_letat_du_modele(client):
    """L'indicateur recopie ce que la sonde vient d'établir : sans lui, un
    modèle absent laisserait toutes les sondes au vert."""
    client.get("/api/ready")
    corps = _lire(client)
    assert "skillseek_modele_appris_disponible" in corps
