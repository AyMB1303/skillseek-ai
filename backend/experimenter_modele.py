"""Recherche d'une représentation exploitable pour l'appréciation des candidatures.

    docker compose exec backend python experimenter_modele.py

Le modèle fondé sur dix-sept indicateurs synthétiques n'apporte aucun gain
mesurable sous le protocole strict. Deux hypothèses sont testées ici pour en
comprendre la raison :

  A. **La question posée est trop fine.** Distinguer « convient bien » de
     « pourrait convenir » relève d'une appréciation subjective. En fusionnant
     ces deux classes, la frontière à apprendre devient plus nette.

  B. **La représentation perd trop d'information.** Comprimer un document de
     cinq mille caractères en dix-sept nombres écarte l'essentiel. Les
     plongements complets du CV et de l'offre, ainsi que leur différence et
     leur produit terme à terme, conservent la totalité du signal capté par
     le modèle de langue.

Toutes les mesures emploient le protocole strict : ni les CV ni les offres du
jeu de test n'apparaissent à l'entraînement.
"""
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services import semantique  # noqa: E402
from app.services.ml import caracteristiques  # noqa: E402

DOSSIER_DONNEES = Path("/app/data")
DOSSIER_CACHE = Path("/app/models/cache")


def journal(message=""):
    print(message, flush=True)


def titre(texte):
    journal(f"\n{'=' * 70}\n{texte}\n{'=' * 70}")


# --------------------------------------------------------------------------
# Découpage strict, commun à toutes les expériences
# --------------------------------------------------------------------------

def decoupage_strict(df, part_test=0.25, graine=42):
    """Sépare CV et offres : aucun élément du test n'a servi à l'entraînement."""
    rng = np.random.RandomState(graine)

    cv = df.resume_text.unique().copy()
    offres = df.job_description_text.unique().copy()
    rng.shuffle(cv)
    rng.shuffle(offres)

    cv_train = set(cv[: int(len(cv) * (1 - part_test))])
    offres_train = set(offres[: int(len(offres) * (1 - part_test))])

    masque_train = (
        df.resume_text.isin(cv_train) & df.job_description_text.isin(offres_train)
    ).values
    masque_test = (
        ~df.resume_text.isin(cv_train) & ~df.job_description_text.isin(offres_train)
    ).values
    return masque_train, masque_test


def evaluer(X, y, masque_train, masque_test, intitule, modele=None):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, f1_score

    if modele is None:
        modele = RandomForestClassifier(
            n_estimators=300, max_depth=12, min_samples_leaf=5,
            class_weight="balanced", random_state=42, n_jobs=-1,
        )

    modele.fit(X[masque_train], y[masque_train])
    predictions = modele.predict(X[masque_test])

    reel = y[masque_test]
    exactitude = accuracy_score(reel, predictions)
    f1 = f1_score(reel, predictions, average="macro")
    reference = pd.Series(reel).value_counts(normalize=True).max()

    journal(
        f"  {intitule:44} {exactitude:>7.1%}  "
        f"(réf. {reference:.1%}, gain {exactitude - reference:+.1%})  F1 {f1:.3f}"
    )
    return {
        "intitule": intitule,
        "exactitude": exactitude,
        "reference": reference,
        "gain": exactitude - reference,
        "f1": f1,
    }


# --------------------------------------------------------------------------
# Représentation par plongements
# --------------------------------------------------------------------------

def plongements(df):
    """Vectorise chaque paire par les plongements du CV et de l'offre.

    Le vecteur final concatène quatre blocs : le CV, l'offre, leur différence
    absolue et leur produit terme à terme. Cette construction est l'usage
    courant pour la classification de paires de textes : la différence
    exprime ce qui les sépare, le produit ce qu'ils partagent.
    """
    cache = DOSSIER_CACHE / "plongements_paires.npy"
    if cache.exists():
        X = np.load(cache)
        if len(X) == len(df):
            journal(f"  Plongements repris du cache : {X.shape}")
            return X

    documents = pd.unique(
        np.concatenate([df.resume_text.values, df.job_description_text.values])
    )
    journal(f"  Encodage de {len(documents)} documents distincts…")

    debut = time.time()
    table = {}
    for index, doc in enumerate(documents):
        vecteur = semantique.encoder(doc)
        if vecteur is None:
            journal("  Modèle de plongements indisponible : expérience abandonnée.")
            return None
        table[doc] = vecteur
        if (index + 1) % 200 == 0:
            journal(f"    {index + 1}/{len(documents)}")
    journal(f"  Encodage terminé en {time.time() - debut:.0f} s")

    blocs = []
    for cv, offre in zip(df.resume_text, df.job_description_text):
        a, b = table[cv], table[offre]
        blocs.append(np.concatenate([a, b, np.abs(a - b), a * b]))

    X = np.vstack(blocs).astype(np.float32)
    DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)
    np.save(cache, X)
    journal(f"  Représentation obtenue : {X.shape}")
    return X


# --------------------------------------------------------------------------

def main():
    train = pd.read_csv(DOSSIER_DONNEES / "resume_fit_train.csv")
    test = pd.read_csv(DOSSIER_DONNEES / "resume_fit_test.csv")
    df = pd.concat([train, test], ignore_index=True)

    masque_train, masque_test = decoupage_strict(df)
    journal(
        f"Découpage strict : {masque_train.sum()} paires d'entraînement, "
        f"{masque_test.sum()} de test"
    )

    y3 = df.label.values
    # Hypothese A : « convient bien » et « pourrait convenir » fusionnes
    y2 = np.where(y3 == "No Fit", "Ne convient pas", "Convient")

    resultats = []

    # ---------------------------------------------------- Indicateurs
    titre("RÉFÉRENCE — dix-sept indicateurs synthétiques")
    X_ind = np.vstack([
        np.load(p) for p in sorted(DOSSIER_CACHE.glob("entrainement_*.npy"))
        + sorted(DOSSIER_CACHE.glob("test_*.npy"))
    ]) if list(DOSSIER_CACHE.glob("entrainement_*.npy")) else None

    if X_ind is None or len(X_ind) != len(df):
        journal("  Vectorisation des indicateurs…")
        X_ind = caracteristiques.construire_lot(
            list(zip(df.resume_text, df.job_description_text)), journal
        )

    resultats.append(evaluer(X_ind, y3, masque_train, masque_test, "Indicateurs — 3 classes"))
    resultats.append(evaluer(X_ind, y2, masque_train, masque_test, "Indicateurs — 2 classes"))

    # ---------------------------------------------------- Plongements
    titre("HYPOTHÈSE B — plongements complets")
    X_emb = plongements(df)

    if X_emb is not None:
        resultats.append(
            evaluer(X_emb, y3, masque_train, masque_test, "Plongements — 3 classes")
        )
        resultats.append(
            evaluer(X_emb, y2, masque_train, masque_test, "Plongements — 2 classes")
        )

        # Sur un espace de grande dimension, un modele lineaire regularise est
        # souvent plus adapte qu'une foret : il exploite l'ensemble des
        # dimensions plutot que d'en selectionner quelques-unes.
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        lineaire = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=2000, class_weight="balanced", C=0.1),
        )
        resultats.append(
            evaluer(X_emb, y2, masque_train, masque_test,
                    "Plongements — 2 classes, modèle linéaire", lineaire)
        )

        # ------------------------------------------------ Combinaison
        titre("COMBINAISON — plongements et indicateurs")
        X_mixte = np.hstack([X_emb, X_ind])
        resultats.append(
            evaluer(X_mixte, y2, masque_train, masque_test, "Combinaison — 2 classes")
        )

    # ---------------------------------------------------- Bilan
    titre("BILAN")
    resultats.sort(key=lambda r: r["gain"], reverse=True)
    journal(f"  {'Configuration':46}{'Gain':>8}{'Exactitude':>12}{'F1':>8}")
    journal("  " + "-" * 68)
    for r in resultats:
        journal(
            f"  {r['intitule']:46}{r['gain']:>+7.1%}"
            f"{r['exactitude']:>12.1%}{r['f1']:>8.3f}"
        )

    meilleur = resultats[0]
    journal("")
    if meilleur["gain"] >= 0.08:
        journal(
            f"  Configuration exploitable : {meilleur['intitule']}\n"
            f"  Gain de {meilleur['gain']:+.1%} sur la référence, sous protocole strict."
        )
    elif meilleur["gain"] >= 0.03:
        journal(
            f"  Gain modeste : {meilleur['gain']:+.1%} pour « {meilleur['intitule']} ».\n"
            f"  Utilisable comme signal d'appoint, non comme critère principal."
        )
    else:
        journal(
            "  Aucune configuration n'apporte de gain significatif sous protocole\n"
            "  strict. Le corpus ne permet pas d'apprendre l'adéquation entre un CV\n"
            "  et une offre au-delà de ce que capturent déjà les règles métiers."
        )


if __name__ == "__main__":
    main()
