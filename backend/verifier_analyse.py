"""Vérification du pipeline d'analyse — à lancer dans le conteneur.

    docker compose exec backend python verifier_analyse.py

Contrôle que les modèles lourds sont bien chargés (spaCy, plongements
lexicaux, Tesseract) et déroule une analyse complète sur un CV d'exemple.
"""
import sys


def titre(texte):
    print(f"\n{'=' * 62}\n{texte}\n{'=' * 62}")


# ---------------------------------------------------------------- Modèles
titre("1. DISPONIBILITÉ DES MODÈLES")

etat = {}

try:
    import spacy
    try:
        spacy.load("fr_core_news_sm")
        etat["spaCy (fr_core_news_sm)"] = "OK"
    except OSError:
        etat["spaCy (fr_core_news_sm)"] = "MODÈLE ABSENT"
except ImportError:
    etat["spaCy (fr_core_news_sm)"] = "NON INSTALLÉ"

try:
    from sentence_transformers import SentenceTransformer  # noqa: F401
    etat["Sentence Transformers"] = "OK"
except ImportError:
    etat["Sentence Transformers"] = "NON INSTALLÉ"

try:
    import pytesseract
    pytesseract.get_tesseract_version()
    etat["Tesseract (OCR)"] = "OK"
except Exception:
    etat["Tesseract (OCR)"] = "NON DISPONIBLE"

try:
    import pdfplumber  # noqa: F401
    etat["pdfplumber (PDF)"] = "OK"
except ImportError:
    etat["pdfplumber (PDF)"] = "NON INSTALLÉ"

try:
    import docx  # noqa: F401
    etat["python-docx (DOCX)"] = "OK"
except ImportError:
    etat["python-docx (DOCX)"] = "NON INSTALLÉ"

for nom, statut in etat.items():
    marque = "✓" if statut == "OK" else "✗"
    print(f"  {marque} {nom:34} {statut}")

if any(s != "OK" for s in etat.values()):
    print("\n  Un composant manquant n'empêche pas l'analyse : un repli est prévu.")

# ---------------------------------------------------------------- Analyse
titre("2. ANALYSE D'UN CV D'EXEMPLE")

from app.services.analyse import analyser_texte  # noqa: E402


class OffreExemple:
    title = "Développeur Python Senior"
    description = (
        "Conception d'interfaces de programmation REST et de traitements de "
        "données. Environnement conteneurisé avec intégration continue."
    )
    required_skills = ["python", "sql", "docker"]
    preferred_skills = ["power bi", "kubernetes", "machine learning"]
    min_experience_years = 3
    min_degree = "Bac+3"


CV = """AYMEN BENRBIB
Ingénieur en systèmes d'information
aymen.benrbib@example.com | +212 6 12 34 56 78 | linkedin.com/in/aymenbenrbib

EXPÉRIENCE PROFESSIONNELLE

Janvier 2022 – Présent
Développeur Full Stack Senior chez TechCorp Maroc
  Conception d'API REST avec Flask et PostgreSQL
  Mise en place de pipelines CI/CD avec Docker

Septembre 2019 – Décembre 2021
Développeur Python chez DataSoft
  Traitements de données et tableaux de bord Power BI

FORMATION
2024 - Master en Ingénierie des Systèmes d'Information, École des Sciences de l'Information
2019 - Licence en Informatique, Université Mohammed V

CERTIFICATIONS
AWS Certified Developer Associate (2023)
Professional Scrum Master I - Scrum.org (2022)

COMPÉTENCES
Python, SQL, Docker, Flask, PostgreSQL, Power BI, Machine Learning, Git

LANGUES
Français : bilingue
Anglais : courant
Arabe : langue maternelle
"""

score, details = analyser_texte(CV, OffreExemple())
ats = details["profil_ats"]

print(f"\n  SCORE : {score}/100\n")
print("  Composantes du calcul")
for c in details["composantes"]:
    barre = "█" * round(c["valeur"] / c["max"] * 20)
    print(f"    {c['libelle']:32} {c['valeur']:>3}/{c['max']:<3} {barre}")
print(f"    {'TOTAL DES MAXIMA':32} {sum(c['max'] for c in details['composantes']):>7}")

titre("3. PROFIL RECONSTITUÉ (schéma ATS)")

b = ats["basics"]
print(f"\n  Identité   : {b['name']}")
print(f"  Email      : {b['email']}")
print(f"  Téléphone  : {b['phone']}")
print(f"  LinkedIn   : {b['linkedin']}")

print(f"\n  Parcours ({len(ats['work'])} postes, {ats['totalExperienceYears']} ans au total)")
for poste in ats["work"]:
    fin = "présent" if poste["current"] else poste["endDate"]
    print(f"    • {poste['position']}")
    print(f"      {poste['company']} | {poste['startDate']} → {fin} ({poste['months']} mois)")

print(f"\n  Formation (plus haut niveau : {ats['highestDegree']})")
for f in ats["education"]:
    print(f"    • [{f['level']}] {f['studyType'][:58]}")

print(f"\n  Certifications ({len(ats['certificates'])})")
for c in ats["certificates"]:
    print(f"    • {c['name']} — {c['issuer']} ({c['date']})")

print("\n  Langues")
for lang in ats["languages"]:
    print(f"    • {lang['language']:10} {lang['fluency']}")

print(f"\n  Compétences détectées ({len(ats['skills'])})")
print(f"    {', '.join(ats['skills'])}")

print(f"\n  Sections identifiées : {', '.join(ats['sectionsDetectees'])}")

titre("4. QUALIFICATION")

print(f"\n  Obligatoires satisfaites : {details['competences_trouvees'] or 'aucune'}")
print(f"  Obligatoires absentes    : {details['competences_manquantes'] or 'aucune'}")
print(f"  Souhaitées satisfaites   : {details['competences_souhaitees_trouvees'] or 'aucune'}")
print(f"  Souhaitées absentes      : {details['competences_souhaitees_manquantes'] or 'aucune'}")
print(f"  Critères éliminatoires   : {details['eliminatoires'] or 'aucun'}")

sim = details["similarite"]
print(f"\n  Proximité sémantique : {sim['valeur']} (méthode : {sim['methode']})")
if sim["methode"] == "plongements":
    print("    → modèle sémantique actif")
else:
    print("    → repli lexical : le modèle de plongements n'a pas été chargé")

avis = details.get("modele")
if avis:
    print(f"\n  Modèle appris : probabilité {avis['probabilite']:.0%} que le profil convienne")
    print(f"    Score des règles seules : {avis['score_avant_ajustement']}")
    print(
        f"    Ajustement appliqué     : {avis['ajustement']:+} "
        f"(borné à ±{avis['amplitude_maximale']})"
        if avis["applique"]
        else "    Ajustement non appliqué : candidature écartée par une règle"
    )
else:
    print("\n  Modèle appris : indisponible — score calculé par les règles seules")

print(f"\n  Moteur : {details['version_moteur']}\n")

sys.exit(0)
