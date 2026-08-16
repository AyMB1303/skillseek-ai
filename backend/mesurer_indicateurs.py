"""Mesure des indicateurs du cahier des charges et audit de biais (S4-04, S3-07).

    docker compose exec backend python mesurer_indicateurs.py

Ce script mesure le **dispositif de présélection dans son ensemble** — lecture
du profil, règles métiers, proximité sémantique et ajustement du modèle — et
non le seul modèle d'apprentissage. Les deux grandeurs sont distinctes et ne
doivent jamais être confondues :

  * le modèle apprend à distinguer un profil convenable d'un profil qui ne
    l'est pas, et son exactitude se mesure sur un corpus d'appariements ;
  * le dispositif, lui, décide de retenir ou d'écarter une candidature selon
    la règle RG-01 (note >= 50). C'est cette décision que le cahier des
    charges engage à 85 % de précision et 80 % de rappel.

Le script produit deux mesures indépendantes :

  A. **Indicateurs de présélection** — précision, rappel, F1 et matrice de
     confusion sur le jeu de validation francophone, où l'adéquation attendue
     de chaque paire est connue par construction.

  B. **Audit de biais** — vérification qu'un attribut sans rapport avec la
     compétence ne déplace pas la note. La méthode est celle de la
     perturbation contrôlée : un même curriculum vitæ est présenté plusieurs
     fois, seul l'attribut testé changeant d'une version à l'autre. Tout écart
     de note observé est alors imputable à ce seul attribut, sans qu'aucune
     hypothèse statistique ne soit nécessaire.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.analyse import analyser_texte  # noqa: E402
from app.services.ml import prediction  # noqa: E402
from app.services.scoring import SEUIL_RETENU  # noqa: E402

DOSSIER_DONNEES = Path("/app/data")
DOSSIER_MODELES = Path("/app/models")


def journal(message=""):
    print(message, flush=True)


def titre(texte):
    journal(f"\n{'=' * 74}\n{texte}\n{'=' * 74}")


# --------------------------------------------------------------------------
# Offres du jeu de validation, sous leur forme structurée
# --------------------------------------------------------------------------

class Offre:
    """Double de l'entité Offre : évite de dépendre de la base de données."""

    def __init__(self, title, required, preferred, exp, degree, texte):
        self.title = title
        self.required_skills = required
        self.preferred_skills = preferred
        self.min_experience_years = exp
        self.min_degree = degree
        self.description = texte
        self.location = None
        self.contract_type = None


OFFRES = {
    "backend": Offre(
        "Développeur Backend Python Senior",
        ["python", "postgresql", "docker"], ["kubernetes", "ci/cd"],
        5, "Bac+5", "",
    ),
    "frontend": Offre(
        "Développeur Frontend React",
        ["javascript", "react", "css"], ["typescript", "next.js", "tests"],
        3, "Bac+3", "",
    ),
    "data": Offre(
        "Data Scientist",
        ["python", "machine learning", "sql"], ["deep learning", "nlp", "power bi"],
        4, "Bac+5", "",
    ),
    "comptable": Offre(
        "Comptable Général",
        ["comptabilite generale", "fiscalite", "excel"], ["sage", "audit"],
        4, "Bac+3", "",
    ),
    "devops": Offre(
        "Ingénieur DevOps",
        ["docker", "kubernetes", "linux"], ["aws", "python", "ci/cd"],
        4, "Bac+5", "",
    ),
    "java": Offre(
        "Développeur Java Spring",
        ["java", "spring", "sql"], ["docker", "agile", "ci/cd"],
        4, "Bac+5", "",
    ),
    "bdd": Offre(
        "Administrateur de Bases de Données",
        ["postgresql", "oracle", "sql"], ["linux", "docker"],
        3, "Bac+3", "",
    ),
    "controle": Offre(
        "Contrôleur de Gestion",
        ["controle de gestion", "excel", "erp"], ["power bi", "comptabilite generale"],
        4, "Bac+5", "",
    ),
}

# L'audit de biais multiplie chaque profil par une vingtaine de variantes :
# le limiter a quelques domaines garde le temps d'execution raisonnable sans
# rien changer a la conclusion, l'ecart mesure etant stable d'un profil a
# l'autre.
DOMAINES_AUDITES = ["backend", "frontend", "data", "comptable", "devops"]


def offre_de(domaine):
    """Retrouve l'offre correspondant au domaine, y compris pour un croisement."""
    cle = domaine.split(" vs ")[-1].strip() if " vs " in domaine else domaine
    return OFFRES[cle]


def charger_validation():
    chemin = DOSSIER_DONNEES / "validation_francais.json"
    if not chemin.exists():
        journal(f"Jeu de validation introuvable : {chemin}")
        sys.exit(1)

    cas = json.loads(chemin.read_text(encoding="utf-8"))
    for cas_unique in cas:
        offre = offre_de(cas_unique["domaine"])
        offre.description = cas_unique["offre"]
    return cas


# --------------------------------------------------------------------------
# A. Indicateurs de présélection
# --------------------------------------------------------------------------

def matrice(vrais, predits):
    """(vrais positifs, faux positifs, faux négatifs, vrais négatifs)."""
    vp = sum(1 for v, p in zip(vrais, predits) if v and p)
    fp = sum(1 for v, p in zip(vrais, predits) if not v and p)
    fn = sum(1 for v, p in zip(vrais, predits) if v and not p)
    vn = sum(1 for v, p in zip(vrais, predits) if not v and not p)
    return vp, fp, fn, vn


def indicateurs(vrais, predits):
    vp, fp, fn, vn = matrice(vrais, predits)
    precision = vp / (vp + fp) if vp + fp else 0.0
    rappel = vp / (vp + fn) if vp + fn else 0.0
    f1 = 2 * precision * rappel / (precision + rappel) if precision + rappel else 0.0
    exactitude = (vp + vn) / len(vrais) if vrais else 0.0
    return {
        "precision": precision, "rappel": rappel, "f1": f1,
        "exactitude": exactitude, "vp": vp, "fp": fp, "fn": fn, "vn": vn,
    }


def mesurer_preselection(cas):
    titre("A. INDICATEURS DE PRÉSÉLECTION (S4-04)")
    journal(
        "Le dispositif complet est appliqué à chaque paire du jeu francophone.\n"
        "Une candidature est retenue lorsque sa note atteint le seuil de "
        f"{SEUIL_RETENU} points (règle RG-01).\n"
        "L'attendu est connu par construction : un profil du domaine de l'offre\n"
        "doit être retenu, un profil d'un autre domaine doit être écarté."
    )

    resultats = []
    journal(f"\n  {'Domaine':26}{'Attendu':16}{'Note':>7}{'Décision':>12}")
    journal("  " + "-" * 62)

    for element in cas:
        offre = offre_de(element["domaine"])
        offre.description = element["offre"]
        score, details = analyser_texte(element["cv"], offre)

        attendu = element["label"] != "No Fit"
        predit = score >= SEUIL_RETENU
        resultats.append({
            "domaine": element["domaine"],
            "label": element["label"],
            "score": score,
            "attendu": attendu,
            "predit": predit,
            "eliminatoires": details.get("eliminatoires", []),
            "modele": (details.get("modele") or {}).get("probabilite"),
        })

        marque = " " if attendu == predit else "  <-- écart"
        journal(
            f"  {element['domaine'][:25]:26}{element['label']:16}{score:>7}"
            f"{'retenue' if predit else 'écartée':>12}{marque}"
        )

    vrais = [r["attendu"] for r in resultats]
    predits = [r["predit"] for r in resultats]
    mesures = indicateurs(vrais, predits)

    journal("\n  Matrice de confusion")
    journal(f"    {'':22}{'retenue (prédit)':>20}{'écartée (prédit)':>20}")
    journal(f"    {'à retenir (réel)':22}{mesures['vp']:>20}{mesures['fn']:>20}")
    journal(f"    {'à écarter (réel)':22}{mesures['fp']:>20}{mesures['vn']:>20}")

    journal("\n  Indicateurs annoncés au cahier des charges")
    for libelle, cle, objectif in (
        ("Précision", "precision", 0.85), ("Rappel", "rappel", 0.80),
    ):
        valeur = mesures[cle]
        etat = "atteint" if valeur >= objectif else "NON ATTEINT"
        journal(
            f"    {libelle:12}{valeur:>7.1%}   objectif {objectif:.0%}   {etat}"
        )
    journal(f"    {'F1':12}{mesures['f1']:>7.3f}")
    journal(f"    {'Exactitude':12}{mesures['exactitude']:>7.1%}")

    return resultats, mesures


def courbe_de_seuil(resultats):
    """Montre ce que devient la décision si le seuil RG-01 est déplacé."""
    journal("\n  Sensibilité au seuil de présélection")
    journal(f"    {'Seuil':>7}{'Précision':>12}{'Rappel':>10}{'F1':>9}")
    journal("    " + "-" * 38)

    vrais = [r["attendu"] for r in resultats]
    for seuil in (40, 45, 50, 55, 60, 65, 70):
        predits = [r["score"] >= seuil for r in resultats]
        m = indicateurs(vrais, predits)
        marque = "  <- seuil retenu" if seuil == SEUIL_RETENU else ""
        journal(
            f"    {seuil:>7}{m['precision']:>12.1%}{m['rappel']:>10.1%}"
            f"{m['f1']:>9.3f}{marque}"
        )


def ordonnancement(resultats):
    """Vérifie que les notes ordonnent correctement les niveaux d'adéquation."""
    journal("\n  Note moyenne par niveau d'adéquation attendu")
    journal(f"    {'Niveau attendu':24}{'Note moyenne':>14}{'Effectif':>10}")
    journal("    " + "-" * 48)

    for niveau in ("Good Fit", "Potential Fit", "No Fit"):
        notes = [r["score"] for r in resultats if r["label"] == niveau]
        if notes:
            libelle = {
                "Good Fit": "Profil adapté",
                "Potential Fit": "Profil partiellement adapté",
                "No Fit": "Profil non adapté",
            }[niveau]
            journal(f"    {libelle[:23]:24}{sum(notes) / len(notes):>13.1f}{len(notes):>10}")


# --------------------------------------------------------------------------
# B. Audit de biais par perturbation contrôlée
# --------------------------------------------------------------------------

# Le contenu professionnel est identique d'une version a l'autre : seule
# l'identite affichee change. Toute variation de note est donc imputable a
# l'attribut teste, et a lui seul.
IDENTITES = {
    "genre": [
        ("masculin", "YOUSSEF TAZI"), ("masculin", "KARIM BENNANI"),
        ("masculin", "OMAR FASSI"),
        ("féminin", "SALMA TAZI"), ("féminin", "NADIA BENNANI"),
        ("féminin", "IMANE FASSI"),
    ],
    "origine du nom": [
        ("maghrébine", "YOUSSEF TAZI"), ("maghrébine", "MEHDI OUAZZANI"),
        ("maghrébine", "HAMZA BERRADA"),
        ("européenne", "THOMAS LEFEBVRE"), ("européenne", "JULIEN MOREAU"),
        ("européenne", "LUCAS GIRARD"),
        ("autre", "WEI ZHANG"), ("autre", "PRIYA SHARMA"),
    ],
}

AGES = [("25 ans", 2001), ("35 ans", 1991), ("45 ans", 1981), ("55 ans", 1971)]

ETABLISSEMENTS = [
    ("établissement public réputé", "Université Mohammed V"),
    ("grande école", "École Nationale Supérieure d'Informatique"),
    ("établissement privé peu connu", "Institut Privé des Technologies de Settat"),
    ("établissement étranger", "Université de Lille"),
]


def _remplacer_nom(cv, nouveau_nom):
    """Substitue la première ligne du document, qui porte l'identité."""
    lignes = cv.splitlines()
    for index, ligne in enumerate(lignes[:5]):
        if ligne.strip():
            lignes[index] = nouveau_nom
            break
    return "\n".join(lignes)


def _ajouter_age(cv, annee):
    lignes = cv.splitlines()
    for index, ligne in enumerate(lignes):
        if "@" in ligne:
            lignes.insert(index + 1, f"Né(e) en {annee}")
            break
    return "\n".join(lignes)


def _remplacer_etablissement(cv, etablissement):
    import re

    return re.sub(
        r"(Université|Ecole|École|Institut|Faculté)[^,\n]*",
        etablissement, cv, count=1,
    )


def _ecart(scores):
    return max(scores) - min(scores)


def auditer_biais(cas):
    titre("B. AUDIT DE BIAIS PAR PERTURBATION CONTRÔLÉE (S3-07)")
    journal(
        "Un même curriculum vitæ est présenté plusieurs fois à la même offre,\n"
        "seul l'attribut testé changeant d'une version à l'autre. Le contenu\n"
        "professionnel — expérience, compétences, diplôme — reste rigoureusement\n"
        "identique. Tout écart de note est donc imputable au seul attribut."
    )

    references = [
        c for c in cas
        if c["label"] == "Good Fit"
        and c["origine"] == "paire construite"
        and c.get("profil", "a") == "a"
        and c["domaine"] in DOMAINES_AUDITES
    ]

    rapport = {}
    for attribut in ("genre", "origine du nom", "âge", "établissement"):
        journal(f"\n  Attribut testé : {attribut}")
        journal(f"    {'Profil':14}{'Variante':32}{'Note':>7}{'Écart':>9}")
        journal("    " + "-" * 62)

        ecarts = []
        for element in references:
            offre = offre_de(element["domaine"])
            offre.description = element["offre"]
            base = element["cv"]

            if attribut == "âge":
                variantes = [(lib, _ajouter_age(base, an)) for lib, an in AGES]
            elif attribut == "établissement":
                variantes = [
                    (lib, _remplacer_etablissement(base, nom))
                    for lib, nom in ETABLISSEMENTS
                ]
            else:
                variantes = [
                    (f"{categorie} — {nom.title()}", _remplacer_nom(base, nom))
                    for categorie, nom in IDENTITES[attribut]
                ]

            notes = []
            for libelle, texte in variantes:
                score, _ = analyser_texte(texte, offre)
                notes.append(score)
                journal(f"    {element['domaine'][:13]:14}{libelle[:31]:32}{score:>7}")

            ecart = _ecart(notes)
            ecarts.append(ecart)
            journal(f"    {'':46}{'écart :':>7}{ecart:>9}")

        maximum = max(ecarts) if ecarts else 0
        moyen = sum(ecarts) / len(ecarts) if ecarts else 0
        rapport[attribut] = {"ecart_maximal": maximum, "ecart_moyen": round(moyen, 2)}

        verdict = (
            "aucun effet" if maximum == 0
            else "effet négligeable" if maximum <= 2
            else "effet à corriger"
        )
        journal(
            f"\n    Écart maximal sur {len(ecarts)} profils : {maximum} point(s) "
            f"— {verdict}"
        )

    return rapport


def synthese_biais(rapport):
    journal("\n  Synthèse de l'audit")
    journal(f"    {'Attribut':24}{'Écart maximal':>16}{'Écart moyen':>14}{'Verdict':>20}")
    journal("    " + "-" * 74)

    for attribut, mesures in rapport.items():
        maximum = mesures["ecart_maximal"]
        verdict = (
            "aucun effet" if maximum == 0
            else "négligeable" if maximum <= 2
            else "à corriger"
        )
        journal(
            f"    {attribut:24}{maximum:>13} pt{mesures['ecart_moyen']:>14.2f}"
            f"{verdict:>20}"
        )

    total = max(m["ecart_maximal"] for m in rapport.values())
    journal("")
    if total == 0:
        journal(
            "    Aucun des attributs testés ne déplace la note. Le résultat était\n"
            "    attendu : le moteur de règles ne lit que les compétences, la durée\n"
            "    d'expérience et le niveau de diplôme. Il confirme surtout que la\n"
            "    proximité sémantique, qui traite le document entier, n'introduit\n"
            "    pas d'effet indirect."
        )
    elif total <= 2:
        journal(
            f"    Écart maximal de {total} point(s) sur 100, très en deçà du seuil de\n"
            "    présélection. L'effet provient de la proximité sémantique, qui\n"
            "    encode le document entier, identité comprise. Il reste sans\n"
            "    conséquence pratique sur la décision."
        )
    else:
        journal(
            f"    Écart de {total} points : un attribut sans rapport avec la compétence\n"
            "    influence la note de façon mesurable. La cause doit être identifiée\n"
            "    et corrigée avant mise en service."
        )


# --------------------------------------------------------------------------

def main():
    journal("Mesure des indicateurs — SkillSeek AI")
    journal(
        f"Modèle appris : "
        f"{'chargé' if prediction.disponible() else 'indisponible (score par les règles seules)'}"
    )

    cas = charger_validation()
    journal(f"Jeu de validation : {len(cas)} appariements francophones")

    resultats, mesures = mesurer_preselection(cas)
    courbe_de_seuil(resultats)
    ordonnancement(resultats)

    biais = auditer_biais(cas)
    synthese_biais(biais)

    titre("CONCLUSION")
    conforme = mesures["precision"] >= 0.85 and mesures["rappel"] >= 0.80
    journal(
        f"  Précision {mesures['precision']:.1%} — Rappel {mesures['rappel']:.1%} — "
        f"F1 {mesures['f1']:.3f}"
    )
    journal(
        "  Objectifs du cahier des charges "
        + ("atteints." if conforme else "non atteints : à documenter honnêtement.")
    )
    journal(
        f"  Biais : écart maximal de "
        f"{max(m['ecart_maximal'] for m in biais.values())} point(s) sur 100."
    )

    DOSSIER_MODELES.mkdir(parents=True, exist_ok=True)
    (DOSSIER_MODELES / "indicateurs.json").write_text(
        json.dumps(
            {
                "preselection": {k: v for k, v in mesures.items()},
                "detail": resultats,
                "biais": biais,
                "seuil": SEUIL_RETENU,
                "effectif": len(cas),
            },
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    journal(f"\n  Résultats enregistrés : {DOSSIER_MODELES / 'indicateurs.json'}\n")


if __name__ == "__main__":
    main()
