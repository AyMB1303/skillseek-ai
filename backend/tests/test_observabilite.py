"""Mesure, traçabilité et sondes.

Ces éléments ne changent aucun résultat métier : ils rendent le traitement
observable. Ils sont donc particulièrement faciles à casser sans que rien ne
le signale — d'où ces tests.
"""
import time

from app.services import observabilite


# ------------------------------- Chronomètre -------------------------------

def test_chaque_etape_est_mesuree_separement():
    chrono = observabilite.Chronometre()
    with chrono.etape("lente"):
        time.sleep(0.03)
    with chrono.etape("rapide"):
        pass

    mesures = chrono.resultat()
    assert set(mesures["etapes_ms"]) == {"lente", "rapide"}
    assert mesures["etapes_ms"]["lente"] >= 25
    assert mesures["etape_la_plus_longue"] == "lente"
    assert mesures["total_ms"] >= mesures["etapes_ms"]["lente"]


def test_une_etape_en_echec_est_mesuree_puis_signalee():
    """C'est précisément l'étape lente qui casse qu'on cherche à voir."""
    chrono = observabilite.Chronometre()
    try:
        with chrono.etape("extraction"):
            raise RuntimeError("document illisible")
    except RuntimeError:
        pass

    mesures = chrono.resultat()
    assert "extraction" in mesures["etapes_ms"]
    assert mesures["etapes_en_echec"] == ["extraction"]


def test_un_chronometre_vide_ne_leve_pas():
    mesures = observabilite.Chronometre().resultat()
    assert mesures["etapes_ms"] == {}
    assert mesures["etape_la_plus_longue"] is None


# ------------------------------- Provenance -------------------------------

def test_la_provenance_identifie_le_moteur(app):
    with app.app_context():
        p = observabilite.provenance("plongements")
    assert p["version_moteur"] == observabilite.VERSION_MOTEUR
    assert p["commit"]
    assert p["analyse_le"].endswith("Z")


def test_le_modele_semantique_n_est_cite_que_s_il_a_servi(app):
    """Nommer un modèle de plongements sur un repli lexical serait faux."""
    with app.app_context():
        assert observabilite.provenance("tf-idf")["modele_semantique"] is None
        assert observabilite.provenance("plongements")["modele_semantique"]


# --------------------------------- Sondes ---------------------------------

def test_la_sonde_de_vivacite_repond(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_la_sonde_de_disponibilite_detaille_les_dependances(client):
    """Vivacité et disponibilité répondent à deux questions différentes."""
    res = client.get("/api/ready")
    assert res.status_code == 200

    corps = res.get_json()
    assert corps["status"] == "ready"
    assert corps["dependances"]["base_de_donnees"] is True
    # Les modeles d'IA sont rapportes sans etre bloquants : leur absence
    # degrade l'analyse, elle n'empeche pas de servir.
    assert "modele_semantique" in corps["dependances"]
    assert "modele_appris" in corps["dependances"]


def test_chaque_reponse_porte_un_identifiant_de_requete(client):
    res = client.get("/api/health")
    assert res.headers.get("X-Request-ID")


def test_un_identifiant_fourni_est_conserve(client):
    """Ce qui permettra de suivre un appel à travers plusieurs services."""
    res = client.get("/api/health", headers={"X-Request-ID": "trace-amont-42"})
    assert res.headers["X-Request-ID"] == "trace-amont-42"
