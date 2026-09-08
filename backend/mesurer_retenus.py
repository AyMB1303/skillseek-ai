#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mesure le jeu retenu à l'écart : des cas que le moteur n'a jamais vus.

Pourquoi ce script est séparé de « mesurer_indicateurs.py ».

Les huit négatifs difficiles du jeu de validation ont été écrits, puis le
moteur a été modifié jusqu'à en écarter deux. Le chiffre qui en sort est donc
optimiste : il porte sur des données qui ont servi à guider le développement.
C'est le biais le plus banal de l'évaluation, et le plus difficile à voir
depuis l'intérieur.

Un jeu retenu à l'écart corrige cela à une condition, et une seule : **il est
mesuré une fois, après que le moteur a été figé.** Le relancer après une
correction inspirée de son résultat le transformerait en jeu d'entraînement,
et il ne vaudrait plus rien. Le script inscrit donc la date et l'empreinte du
code mesuré, de sorte qu'une mesure faite après une modification se voie.

Usage :

    docker compose exec backend python mesurer_retenus.py

Hors conteneur :

    SKILLSEEK_DONNEES=../data python mesurer_retenus.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.analyse import analyser_texte          # noqa: E402
from app.services.scoring import SEUIL_RETENU            # noqa: E402
from mesurer_indicateurs import OFFRES, offre_de         # noqa: E402

DOSSIER_DONNEES = Path(os.getenv("SKILLSEEK_DONNEES", "/app/data"))
FICHIER = DOSSIER_DONNEES / "negatifs_retenus.txt"
JOURNAL = DOSSIER_DONNEES / "negatifs_retenus_resultat.json"


def lire(chemin: Path):
    """Découpe le fichier en (domaine, curriculum).

    Les lignes de commentaire — celles qui commencent par « > » — sont
    retirées : le mode d'emploi peut rester dans le fichier sans polluer le
    texte analysé.
    """
    if not chemin.exists():
        sys.exit(f"Fichier introuvable : {chemin}")

    cas, domaine, lignes = [], None, []
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if ligne.lstrip().startswith(">"):
            continue
        if ligne.startswith("## "):
            if domaine and "".join(lignes).strip():
                cas.append((domaine, "\n".join(lignes).strip()))
            domaine, lignes = ligne[3:].strip().lower(), []
            continue
        lignes.append(ligne)
    if domaine and "".join(lignes).strip():
        cas.append((domaine, "\n".join(lignes).strip()))
    return cas


def empreinte_du_code():
    """Empreinte du commit mesuré, pour que la mesure soit rattachable."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=Path(__file__).parent,
        ).stdout.strip() or "inconnue"
    except Exception:                                    # pragma: no cover
        return "inconnue"


def main():
    cas = lire(FICHIER)
    if not cas:
        sys.exit("Aucune candidature trouvée : le fichier n'a pas été rempli.")

    inconnus = [d for d, _ in cas if d.split(" (")[0] not in OFFRES]
    if inconnus:
        sys.exit(
            f"Domaine(s) inconnu(s) : {', '.join(sorted(set(inconnus)))}\n"
            f"Domaines acceptés : {', '.join(sorted(OFFRES))}"
        )

    if JOURNAL.exists():
        precedent = json.loads(JOURNAL.read_text(encoding="utf-8"))
        print(
            "\n  AVERTISSEMENT — ce jeu a déjà été mesuré le "
            f"{precedent['date']}, sur le code {precedent['code']}.\n"
            "  Un jeu retenu à l'écart ne vaut que mesuré une fois. Si le\n"
            "  moteur a changé entre-temps, ce second résultat n'est plus\n"
            "  indépendant, et c'est le premier qui doit être publié.\n"
        )

    print("\nJeu retenu à l'écart — écrit sans que le moteur puisse s'y adapter")
    print(f"Code mesuré : {empreinte_du_code()}\n")
    print(f"  {'Domaine':14}{'Note':>6}{'Décision':>12}   Motif principal")
    print("  " + "-" * 74)

    ecartees = 0
    detail = []
    for domaine, cv in cas:
        offre = offre_de(domaine)
        score, d = analyser_texte(cv, offre)
        retenue = score >= SEUIL_RETENU
        ecartees += 0 if retenue else 1
        motif = (d["eliminatoires"] or d["reserves"] or ["—"])[0]
        print(
            f"  {domaine[:13]:14}{score:>6}{'retenue' if retenue else 'écartée':>12}"
            f"   {motif[:44]}"
        )
        detail.append({
            "domaine": domaine, "score": score, "retenue": retenue,
            "eliminatoires": d["eliminatoires"], "reserves": d["reserves"],
            "etayees": d.get("competences_etayees"),
            "declarees": d.get("competences_declarees"),
        })

    total = len(cas)
    print(f"\n  {ecartees} candidature(s) sur {total} correctement écartée(s).")
    print(
        "\n  Ces cas sont tous des profils à écarter : le nombre ci-dessus est\n"
        "  donc la part que le moteur reconnaît comme telle sur des dossiers\n"
        "  qu'il n'a jamais vus. À comparer aux 2 sur 8 du jeu de validation,\n"
        "  dont le résultat est optimiste par construction."
    )

    JOURNAL.write_text(json.dumps({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "code": empreinte_du_code(),
        "total": total,
        "ecartees": ecartees,
        "detail": detail,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Résultat conservé : {JOURNAL}")


if __name__ == "__main__":
    main()
