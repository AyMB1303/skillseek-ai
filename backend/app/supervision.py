"""Exposition des indicateurs d'exploitation au format Prometheus.

Le principe qui gouverne ce fichier : **on n'invente aucune mesure ici.**
L'application chronométrait déjà chaque requête pour l'inscrire au journal, et
conservait déjà le détail de chaque analyse. Ce module ne fait que publier ces
mêmes valeurs sous une forme qu'un collecteur sait lire — il ne mesure rien de
nouveau, il rend lisible ce qui était déjà mesuré.

Deux familles d'indicateurs, et la distinction compte pour l'exploitation.

Les indicateurs **techniques** répondent à « le service va-t-il bien » : débit,
codes de retour, temps de réponse. Ils suffisent à déclencher une alerte, mais
ils ne disent pas ce que le service fait.

Les indicateurs **métier** répondent à « le service fait-il ce qu'on attend » :
combien d'analyses aboutissent, combien échouent, comment se distribuent les
notes produites. Un service peut répondre 200 à toutes les requêtes tout en
notant tout le monde à zéro parce qu'un modèle ne s'est pas chargé — le premier
groupe reste vert, le second le voit.

Le format employé est le format texte de Prometheus, qui fonctionne par
interrogation : le collecteur vient lire cette page à intervalle régulier,
plutôt que l'application ne pousse des valeurs. C'est ce qui permet de savoir
qu'un service ne répond plus — un service muet qu'on interroge se remarque,
un service muet qui devait pousser ne se distingue pas d'un service calme.
"""
from __future__ import annotations

import time

from flask import Response, g, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Registre dédié plutôt que le registre global : deux appels à la fabrique
# d'application — ce que font les tests — enregistreraient deux fois les mêmes
# indicateurs et lèveraient une erreur de duplication.
REGISTRE = CollectorRegistry()

# --------------------------------------------------------------------------
# Indicateurs techniques
# --------------------------------------------------------------------------

REQUETES = Counter(
    "skillseek_requetes_total",
    "Requêtes HTTP traitées.",
    # Le chemin brut ne convient pas comme étiquette : « /api/offers/1 » et
    # « /api/offers/2 » créeraient une série chacune, et le nombre de séries
    # croîtrait avec les données. On emploie la règle de routage, qui est un
    # ensemble fini : « /api/offers/<int:id> ».
    ["methode", "route", "code"],
    registry=REGISTRE,
)

DUREE_REQUETE = Histogram(
    "skillseek_duree_requete_secondes",
    "Temps de traitement d'une requête HTTP.",
    ["methode", "route"],
    # Bornes choisies d'après les durées observées : la majorité des appels
    # répond sous 100 ms, l'analyse d'un curriculum en demande quelques
    # secondes. Des bornes par défaut, taillées pour des services rapides,
    # regrouperaient toutes les analyses dans le même seau et rendraient le
    # 95e centile inexploitable.
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
    registry=REGISTRE,
)

# --------------------------------------------------------------------------
# Indicateurs métier
# --------------------------------------------------------------------------

ANALYSES = Counter(
    "skillseek_analyses_total",
    "Analyses de curriculum menées à leur terme.",
    # « resultat » vaut « aboutie » ou « indisponible ». C'est la distinction
    # que le service applique déjà : une analyse qui échoue ne perd jamais la
    # candidature, elle produit un état explicite.
    ["resultat"],
    registry=REGISTRE,
)

DUREE_ANALYSE = Histogram(
    "skillseek_duree_analyse_secondes",
    "Temps d'analyse d'un curriculum, de la lecture à la note.",
    buckets=(0.5, 1, 2, 3, 5, 8, 12, 20, 30, 60),
    registry=REGISTRE,
)

NOTES = Histogram(
    "skillseek_note_produite",
    "Distribution des notes produites par le moteur.",
    # Le seuil de présélection est à 50 : les bornes l'encadrent pour que la
    # part des candidatures écartées se lise directement sur l'histogramme.
    buckets=(10, 20, 30, 40, 50, 60, 70, 80, 90, 100),
    registry=REGISTRE,
)

MODELE_CHARGE = Gauge(
    "skillseek_modele_appris_disponible",
    "1 si le modèle d'ajustement est chargé, 0 sinon.",
    registry=REGISTRE,
)


def observer_analyse(secondes: float, note: float | None, aboutie: bool) -> None:
    """Publie le résultat d'une analyse.

    Appelée à l'endroit où la candidature est enregistrée, donc là où le
    résultat est déjà connu : aucune mesure supplémentaire n'est prise.
    """
    ANALYSES.labels(resultat="aboutie" if aboutie else "indisponible").inc()
    DUREE_ANALYSE.observe(secondes)
    if aboutie and note is not None:
        NOTES.observe(float(note))


def brancher(app) -> None:
    """Greffe l'observation sur le cycle de requête et expose « /metrics »."""

    @app.before_request
    def _demarrer_chrono():
        # Le chronomètre existant sert au journal ; on ne le double pas.
        if not hasattr(g, "debut_requete"):
            g.debut_requete = time.perf_counter()

    @app.after_request
    def _observer(reponse):
        debut = g.get("debut_requete")
        # La règle de routage plutôt que le chemin : voir le commentaire des
        # étiquettes. Une requête sur une route inconnue est rangée sous
        # « inconnue » pour la même raison — sinon un balayage automatisé
        # créerait autant de séries que d'URL tentées.
        route = request.url_rule.rule if request.url_rule else "inconnue"
        if debut is not None and not route.startswith("/static"):
            REQUETES.labels(
                methode=request.method, route=route, code=reponse.status_code
            ).inc()
            DUREE_REQUETE.labels(methode=request.method, route=route).observe(
                time.perf_counter() - debut
            )
        return reponse

    @app.get("/metrics")
    def metriques():
        """Page lue par le collecteur.

        Elle n'est pas exposée au public : le point d'entrée du cluster ne la
        route pas, et seule une politique réseau autorise le collecteur à
        joindre le service. Une page d'indicateurs renseigne un attaquant sur
        le trafic, les chemins existants et les moments creux.
        """
        return Response(generate_latest(REGISTRE), mimetype=CONTENT_TYPE_LATEST)
