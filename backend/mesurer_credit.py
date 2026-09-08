"""Balayage du crédit accordé à une compétence citée mais non étayée.

    docker compose exec backend python mesurer_credit.py

Le moteur distingue une compétence **étayée** — une expérience datée la décrit
en train d'être exercée — d'une compétence seulement **déclarée**, présente
dans la rubrique des compétences et nulle part ailleurs. La seconde vaut
`CREDIT_DECLAREE` fois la première dans le calcul de la part « compétences ».

Ce script répond à deux questions, et à elles seules :

  1. **Le signal existe-t-il ?** Quelle part de ses compétences obligatoires un
     profil adapté étaye-t-il, comparée à un négatif difficile ? Si les deux
     parts sont voisines, la distinction ne sépare rien et le paramètre est
     sans objet.

  2. **Quelle valeur retenir ?** Le dispositif complet est remesuré pour
     plusieurs crédits. Le tableau produit est la seule justification
     admissible du réglage : un paramètre choisi sans lui serait choisi au
     jugé.

Le balayage réutilise la machinerie de `mesurer_indicateurs.py` — mêmes offres,
même jeu, même chaîne d'analyse — pour que les deux mesures soient comparables.
Aucun état n'est écrit : ce script lit, calcule et affiche.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services import ats, scoring  # noqa: E402
from app.services.analyse import analyser_texte  # noqa: E402
from mesurer_indicateurs import (  # noqa: E402
    charger_validation,
    indicateurs,
    journal,
    offre_de,
    titre,
)

# Les valeurs balayées. 1,00 est le comportement d'avant la distinction ;
# 0,00 signifierait qu'une compétence non racontée n'est pas acquise.
CREDITS = [1.00, 0.90, 0.80, 0.75, 0.70, 0.60, 0.50, 0.35, 0.20, 0.00]


def part_etayee(cas):
    """Part des compétences obligatoires trouvées qui sont aussi étayées.

    Mesure l'extraction seule — ni le modèle appris ni la proximité sémantique
    n'interviennent — donc reproductible partout où le dépôt est installé.
    """
    offre = offre_de(cas["domaine"])
    offre.description = cas["offre"]

    profil_ats = ats.analyser_cv(cas["cv"])
    profil = ats.vers_profil_scoring(profil_ats)

    possedees = {s.lower() for s in profil.get("skills") or []}
    etayees = {s.lower() for s in profil.get("skills_etayees") or []}

    trouvees = [
        canonique
        for canonique, _ in scoring.exigences_canoniques(offre.required_skills)
        if canonique in possedees
    ]
    if not trouvees:
        return None
    return sum(1 for s in trouvees if s in etayees) / len(trouvees)


def mesurer_signal(cas):
    titre("LE SIGNAL EXISTE-T-IL ?")
    journal(
        "Part des compétences obligatoires trouvées dans le curriculum qui sont\n"
        "en outre décrites par une expérience datée. Les négatifs difficiles\n"
        "sont les paires dont le domaine porte la mention « (difficile) »."
    )

    groupes = {"Profil adapté": [], "Négatif difficile": [], "Autre domaine": []}
    for element in cas:
        part = part_etayee(element)
        if part is None:
            continue
        if "(difficile)" in element["domaine"]:
            groupes["Négatif difficile"].append(part)
        elif element["label"] == "No Fit":
            groupes["Autre domaine"].append(part)
        else:
            groupes["Profil adapté"].append(part)

    journal(f"\n  {'Groupe':22}{'Part étayée':>14}{'Effectif':>11}")
    journal("  " + "-" * 47)
    for nom, parts in groupes.items():
        if not parts:
            continue
        journal(f"  {nom:22}{sum(parts) / len(parts):>13.0%}{len(parts):>11}")

    adaptes = groupes["Profil adapté"]
    durs = groupes["Négatif difficile"]
    if adaptes and durs:
        ecart = sum(adaptes) / len(adaptes) - sum(durs) / len(durs)
        journal(
            f"\n  Écart entre profils adaptés et négatifs difficiles : "
            f"{ecart:.0%} de part étayée."
        )
        journal(
            "  Un écart proche de zéro signifierait que la distinction ne sépare\n"
            "  rien, et qu'aucun réglage du crédit ne peut améliorer la précision."
        )
    return groupes


def balayer(cas):
    titre("QUEL CRÉDIT RETENIR ?")
    journal(
        "Le dispositif complet est remesuré pour chaque valeur. La valeur\n"
        f"actuellement inscrite dans le moteur est {scoring.CREDIT_DECLAREE:.2f}."
    )

    initial = scoring.CREDIT_DECLAREE
    lignes = []
    try:
        for credit in CREDITS:
            scoring.CREDIT_DECLAREE = credit
            vrais, predits = [], []
            for element in cas:
                offre = offre_de(element["domaine"])
                offre.description = element["offre"]
                score, _ = analyser_texte(element["cv"], offre)
                vrais.append(element["label"] != "No Fit")
                predits.append(score >= scoring.SEUIL_RETENU)
            lignes.append((credit, indicateurs(vrais, predits)))
    finally:
        # Le moteur doit ressortir de ce script exactement comme il y est entré.
        scoring.CREDIT_DECLAREE = initial

    journal(f"\n  {'Crédit':>8}{'Précision':>12}{'Rappel':>10}{'F1':>9}   ")
    journal("  " + "-" * 41)
    for credit, mesure in lignes:
        marque = "  <- retenu" if abs(credit - initial) < 1e-9 else ""
        journal(
            f"  {credit:>8.2f}{mesure['precision']:>11.1%}{mesure['rappel']:>10.1%}"
            f"{mesure['f1']:>9.3f}{marque}"
        )

    journal(
        "\n  Prudence de lecture : avec huit négatifs difficiles, une seule\n"
        "  décision qui bascule déplace la précision d'environ deux points et\n"
        "  demi. Un maximum isolé sur ce tableau est du bruit, pas un optimum ;\n"
        "  seule une tendance étendue sur plusieurs valeurs est interprétable."
    )
    return lignes


def main():
    journal("Balayage du crédit d'une compétence déclarée — SkillSeek AI")
    cas = charger_validation()
    journal(f"Jeu de validation : {len(cas)} appariements francophones")

    mesurer_signal(cas)
    balayer(cas)

    journal(
        "\nAucun fichier n'a été modifié : la valeur du moteur est inchangée."
    )


if __name__ == "__main__":
    main()
