"""Entraînement du modèle d'appréciation des candidatures.

    docker compose exec backend python entrainer_modele.py
    docker compose exec backend python entrainer_modele.py --revectoriser

Le modèle répond à une question binaire : **ce profil convient-il à cette
offre ?** La formulation initiale, à trois niveaux, distinguait « convient
bien » de « pourrait convenir ». Les mesures ont montré qu'elle était
inapprenable sur ce corpus — le gain plafonnait à 0,4 % — cette distinction
relevant d'une appréciation subjective que 477 profils ne suffisent pas à
faire apprendre. Ramenée à deux classes, la tâche devient exploitable.

Quatre protocoles d'évaluation sont appliqués, du plus permissif au plus
exigeant. Leur comparaison montre à quel point une conclusion dépend du
protocole qui l'établit :

  1. **Découpage d'origine** — sépare les offres, partage les CV.
  2. **Découpage par CV** — CV inconnus, offres déjà vues.
  3. **Découpage strict** — ni CV ni offres connus. Seule mesure
     représentative de la plateforme, où un candidat inconnu postule à une
     offre nouvellement publiée. Le modèle livré est celui de ce protocole.
  4. **Validation française** — vérifie que le modèle, appris sur des
     documents anglais, opère sur des documents français.

Les vecteurs sont mis en cache : seule la première exécution supporte le coût
de l'analyse des documents.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ml import caracteristiques  # noqa: E402

DOSSIER_DONNEES = Path("/app/data")
DOSSIER_MODELES = Path("/app/models")
DOSSIER_CACHE = DOSSIER_MODELES / "cache"

CONVIENT = "Convient"
NE_CONVIENT_PAS = "Ne convient pas"
CLASSES = [NE_CONVIENT_PAS, CONVIENT]


def journal(message=""):
    print(message, flush=True)


def titre(texte):
    journal(f"\n{'=' * 70}\n{texte}\n{'=' * 70}")


def binariser(etiquettes):
    """Ramène les trois niveaux d'origine à la question effectivement posée."""
    return np.where(etiquettes == "No Fit", NE_CONVIENT_PAS, CONVIENT)


# --------------------------------------------------------------------------
# Chargement et vectorisation
# --------------------------------------------------------------------------

def charger():
    fichiers = {
        "train": DOSSIER_DONNEES / "resume_fit_train.csv",
        "test": DOSSIER_DONNEES / "resume_fit_test.csv",
    }
    for chemin in fichiers.values():
        if not chemin.exists():
            journal(f"Fichier introuvable : {chemin}")
            sys.exit(1)

    train = pd.read_csv(fichiers["train"])
    test = pd.read_csv(fichiers["test"])
    journal(f"Corpus : {len(train)} paires d'entraînement, {len(test)} de test.")
    journal(
        f"CV distincts : {train.resume_text.nunique()} / {test.resume_text.nunique()} — "
        f"offres distinctes : {train.job_description_text.nunique()} / "
        f"{test.job_description_text.nunique()}"
    )
    return train, test


def _empreinte(df):
    contenu = f"{len(df)}|{df.resume_text.iloc[0][:200]}|{'|'.join(caracteristiques.NOMS)}"
    return hashlib.md5(contenu.encode("utf-8")).hexdigest()[:12]


def vectoriser(df, etiquette, forcer=False):
    DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)
    cache = DOSSIER_CACHE / f"{etiquette}_{_empreinte(df)}.npy"

    if cache.exists() and not forcer:
        X = np.load(cache)
        journal(f"\nVecteurs repris du cache — {etiquette} ({X.shape[0]} paires)")
        return X

    journal(f"\nVectorisation — {etiquette} ({len(df)} paires)")
    debut = time.time()
    X = caracteristiques.construire_lot(
        list(zip(df.resume_text, df.job_description_text)), journal
    )
    np.save(cache, X)
    journal(f"  terminé en {time.time() - debut:.0f} s — {X.shape[1]} caractéristiques")
    return X


# --------------------------------------------------------------------------
# Apprentissage et évaluation
# --------------------------------------------------------------------------

def entrainer(X, y):
    from sklearn.ensemble import RandomForestClassifier

    return RandomForestClassifier(
        n_estimators=300,
        max_depth=12,              # limite la memorisation des exemples
        min_samples_leaf=5,
        max_features="sqrt",
        class_weight="balanced",   # compense le desequilibre des classes
        random_state=42,
        n_jobs=-1,
    ).fit(X, y)


def evaluer(modele, X, y, intitule, detail=True):
    from sklearn.metrics import (
        accuracy_score, classification_report, confusion_matrix,
        f1_score, precision_score, recall_score, roc_auc_score
    )

    predictions = modele.predict(X)
    exactitude = accuracy_score(y, predictions)
    f1 = f1_score(y, predictions, pos_label=CONVIENT)
    precision = precision_score(y, predictions, pos_label=CONVIENT, zero_division=0)
    rappel = recall_score(y, predictions, pos_label=CONVIENT)
    reference = pd.Series(y).value_counts(normalize=True).max()

    aire = None
    if len(set(y)) == 2:
        indice = list(modele.classes_).index(CONVIENT)
        aire = roc_auc_score(
            (y == CONVIENT).astype(int), modele.predict_proba(X)[:, indice]
        )

    journal(f"\n  {intitule}")
    journal(f"    Exactitude                     : {exactitude:.1%}")
    journal(f"    Référence (classe majoritaire) : {reference:.1%}")
    journal(f"    Gain sur référence             : {exactitude - reference:+.1%}")
    journal(f"    Précision sur « {CONVIENT} »      : {precision:.1%}")
    journal(f"    Rappel sur « {CONVIENT} »         : {rappel:.1%}")
    journal(f"    F1                             : {f1:.3f}")
    if aire is not None:
        journal(f"    Aire sous la courbe ROC        : {aire:.3f}")

    if detail:
        journal("\n    Détail par classe :")
        for ligne in classification_report(
            y, predictions, zero_division=0, digits=3
        ).splitlines()[1:]:
            if ligne.strip():
                journal(f"      {ligne}")

        journal("\n    Matrice de confusion (lignes = réel, colonnes = prédit) :")
        presentes = [c for c in CLASSES if c in set(y) | set(predictions)]
        matrice = confusion_matrix(y, predictions, labels=presentes)
        journal("      " + " " * 18 + "".join(f"{c:>18}" for c in presentes))
        for nom, ligne in zip(presentes, matrice):
            journal(f"      {nom:18}" + "".join(f"{v:>18}" for v in ligne))

    return {
        "protocole": intitule,
        "exactitude": round(float(exactitude), 4),
        "reference": round(float(reference), 4),
        "gain": round(float(exactitude - reference), 4),
        "precision": round(float(precision), 4),
        "rappel": round(float(rappel), 4),
        "f1": round(float(f1), 4),
        "auc": round(float(aire), 4) if aire is not None else None,
        "effectif_test": int(len(y)),
    }


def importances(modele, limite=10):
    journal("\n  Contribution des caractéristiques :")
    paires = sorted(
        zip(caracteristiques.NOMS, modele.feature_importances_),
        key=lambda p: p[1], reverse=True,
    )
    for nom, poids in paires[:limite]:
        journal(f"    {nom:28} {poids:.3f}  {'#' * int(poids * 140)}")


# --------------------------------------------------------------------------
# Protocoles
# --------------------------------------------------------------------------

def _decouper(df, colonnes, part_test=0.25, graine=42):
    """Sépare le corpus : aucun élément du test n'a servi à l'entraînement."""
    rng = np.random.RandomState(graine)
    retenues = {}
    for colonne in colonnes:
        valeurs = df[colonne].unique().copy()
        rng.shuffle(valeurs)
        retenues[colonne] = set(valeurs[: int(len(valeurs) * (1 - part_test))])

    train = np.ones(len(df), dtype=bool)
    test = np.ones(len(df), dtype=bool)
    for colonne, gardees in retenues.items():
        appartient = df[colonne].isin(gardees).values
        train &= appartient
        test &= ~appartient
    return train, test


def protocole_origine(Xtr, ytr, Xte, yte):
    titre("PROTOCOLE 1 — Découpage d'origine")
    journal(
        "Le découpage fourni sépare les offres mais partage les CV. Il mesure la\n"
        "capacité à traiter une offre nouvelle avec des profils déjà rencontrés."
    )
    return evaluer(entrainer(Xtr, ytr), Xte, yte, "Découpage d'origine")


def protocole_par_cv(df, X, y):
    titre("PROTOCOLE 2 — Découpage par CV")
    journal(
        "Aucun CV du test n'a été vu à l'entraînement, mais les offres sont\n"
        "communes aux deux jeux."
    )
    tr, te = _decouper(df, ["resume_text"])
    journal(f"\n  {tr.sum()} paires d'entraînement, {te.sum()} de test")
    return evaluer(entrainer(X[tr], y[tr]), X[te], y[te], "Découpage par CV")


def protocole_strict(df, X, y):
    titre("PROTOCOLE 3 — Découpage strict (CV et offres disjoints)")
    journal(
        "Ni les CV ni les offres du test n'ont été vus. C'est la situation réelle\n"
        "de la plateforme : un candidat inconnu postule à une offre nouvellement\n"
        "publiée. Le modèle livré est celui de ce protocole."
    )
    tr, te = _decouper(df, ["resume_text", "job_description_text"])
    journal(
        f"\n  {tr.sum()} paires d'entraînement ({df.loc[tr].resume_text.nunique()} CV, "
        f"{df.loc[tr].job_description_text.nunique()} offres)"
    )
    journal(f"  {te.sum()} paires de test")

    modele = entrainer(X[tr], y[tr])
    resultat = evaluer(modele, X[te], y[te], "Découpage strict")
    importances(modele)
    return resultat, modele


def protocole_francais(modele):
    titre("PROTOCOLE 4 — Validation française (transfert interlangue)")
    chemin = DOSSIER_DONNEES / "validation_francais.json"
    if not chemin.exists():
        journal(f"Jeu de validation absent : {chemin} — protocole ignoré.")
        return None

    cas = json.loads(chemin.read_text(encoding="utf-8"))
    positifs = sum(1 for c in cas if c["label"] != "No Fit")
    journal(
        f"Le modèle a été appris sur des documents anglais. Il est évalué ici sur\n"
        f"{len(cas)} paires françaises jamais vues ({positifs} profils à retenir,\n"
        f"{len(cas) - positifs} à écarter). Ce protocole établit que le transfert\n"
        f"d'une langue à l'autre opère ; l'échantillon reste trop restreint pour\n"
        f"valoir mesure de référence."
    )
    X = caracteristiques.construire_lot([(c["cv"], c["offre"]) for c in cas])
    y = binariser(np.array([c["label"] for c in cas]))
    return evaluer(modele, X, y, "Validation française")


# --------------------------------------------------------------------------

def main():
    forcer = "--revectoriser" in sys.argv
    try:
        import sklearn  # noqa: F401
    except ImportError:
        journal("scikit-learn est absent. Reconstruisez le conteneur.")
        sys.exit(1)

    train, test = charger()
    Xtr = vectoriser(train, "entrainement", forcer)
    Xte = vectoriser(test, "test", forcer)

    ytr = binariser(train.label.values)
    yte = binariser(test.label.values)
    journal(f"\nQuestion posée : « {CONVIENT} » ou « {NE_CONVIENT_PAS} »")
    journal(
        f"  Répartition : {(ytr == CONVIENT).mean():.1%} de profils convenables "
        f"à l'entraînement"
    )

    df = pd.concat([train, test], ignore_index=True)
    X = np.vstack([Xtr, Xte])
    y = np.concatenate([ytr, yte])

    resultats = [
        protocole_origine(Xtr, ytr, Xte, yte),
        protocole_par_cv(df, X, y),
    ]
    resultat_strict, modele = protocole_strict(df, X, y)
    resultats.append(resultat_strict)

    resultat_fr = protocole_francais(modele)
    if resultat_fr:
        resultats.append(resultat_fr)

    # ---------------------------------------------------------------- Bilan
    titre("SYNTHÈSE")
    journal(
        f"  {'Protocole':24}{'Exactitude':>12}{'Référence':>12}"
        f"{'Gain':>9}{'F1':>8}{'AUC':>8}"
    )
    journal("  " + "-" * 72)
    for r in resultats:
        auc = f"{r['auc']:.3f}" if r["auc"] is not None else "—"
        journal(
            f"  {r['protocole']:24}{r['exactitude']:>11.1%}{r['reference']:>12.1%}"
            f"{r['gain']:>+9.1%}{r['f1']:>8.3f}{auc:>8}"
        )

    journal(
        f"\n  Mesure retenue pour le rapport : protocole strict, "
        f"{resultat_strict['exactitude']:.1%} d'exactitude "
        f"({resultat_strict['gain']:+.1%} sur la référence)."
    )

    # ------------------------------------------------------- Enregistrement
    DOSSIER_MODELES.mkdir(parents=True, exist_ok=True)
    import joblib

    joblib.dump(
        {
            "modele": modele,
            "caracteristiques": caracteristiques.NOMS,
            "classes": list(modele.classes_),
            "classe_positive": CONVIENT,
            "version": "rf-binaire-1.0",
            "protocole_reference": "strict",
            "evaluation": resultat_strict,
        },
        DOSSIER_MODELES / "correspondance.joblib",
    )
    (DOSSIER_MODELES / "evaluation.json").write_text(
        json.dumps(resultats, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    journal(f"\n  Modèle    : {DOSSIER_MODELES / 'correspondance.joblib'}")
    journal(f"  Résultats : {DOSSIER_MODELES / 'evaluation.json'}\n")


if __name__ == "__main__":
    main()
