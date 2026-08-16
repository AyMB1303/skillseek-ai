"""Mécanismes destinés à contenir le temps de réponse de l'assistant.

Ces optimisations sont invisibles dans la réponse rendue : rien ne signale
qu'un sondage a été évité ou qu'un encodage s'est fait en une passe. Les
figer par des tests est le seul moyen qu'une modification ultérieure ne les
défasse pas en silence.
"""
from app.services import semantique
from app.services.rag import generation, index


def test_la_disponibilite_du_modele_local_n_est_pas_resondee(monkeypatch):
    """Sans cache, chaque question payait un aller-retour — ou un délai complet."""
    appels = []

    def faux_urlopen(*_args, **_kwargs):
        appels.append(1)
        raise OSError("service arrêté")

    monkeypatch.setattr(generation.urllib.request, "urlopen", faux_urlopen)
    generation._sondage.update(instant=0.0, disponible=False)

    assert generation.ollama_disponible(force=True) is False
    for _ in range(5):
        generation.ollama_disponible()

    assert len(appels) == 1, "le sondage a été refait alors qu'il était encore valide"


def test_le_sondage_peut_etre_force(monkeypatch):
    monkeypatch.setattr(
        generation.urllib.request, "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(OSError("arrêté")),
    )
    generation._sondage.update(instant=0.0, disponible=False)
    generation.ollama_disponible(force=True)
    # Le forçage existe pour un diagnostic explicite, pas pour le flux normal.
    assert generation.ollama_disponible(force=True) is False


def test_la_methode_de_recherche_est_retenue(monkeypatch):
    """Interroger le modèle à chaque réponse revenait à encoder un texte pour rien."""
    appels = []
    monkeypatch.setattr(
        semantique, "encoder", lambda t: appels.append(t) or None
    )
    index._methode = None

    assert index.methode_active() == "lexicale"
    index.methode_active()
    index.methode_active()
    assert len(appels) == 1


def test_l_encodage_par_lot_respecte_l_ordre_et_le_cache(monkeypatch):
    """Le lot doit rendre les vecteurs dans l'ordre reçu, cache compris."""
    class ModeleFactice:
        def encode(self, textes, **_kwargs):
            if isinstance(textes, str):
                return f"vecteur:{textes}"
            return [f"vecteur:{t}" for t in textes]

    monkeypatch.setattr(semantique, "_charger_modele", lambda: ModeleFactice())
    semantique._cache_plongements.clear()

    # « b » est déjà connu : il doit être repris du cache sans décaler les autres.
    semantique.encoder("b")
    resultats = semantique.encoder_lot(["a", "b", "c"])

    assert resultats == ["vecteur:a", "vecteur:b", "vecteur:c"]
    semantique._cache_plongements.clear()


def test_l_encodage_par_lot_sans_modele_ne_leve_pas(monkeypatch):
    monkeypatch.setattr(semantique, "_charger_modele", lambda: None)
    assert semantique.encoder_lot(["a", "b"]) == [None, None]
