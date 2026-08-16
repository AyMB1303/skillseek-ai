"""Modèle d'apprentissage supervisé pour l'appréciation d'une candidature.

Le modèle complète le moteur de règles : là où celui-ci vérifie des critères
explicites, le modèle apprend sur des décisions réelles ce qui distingue un
profil adapté d'un profil qui ne l'est pas.

  * `caracteristiques` : transformation d'une paire (CV, offre) en vecteur ;
  * `entrainement`     : apprentissage et évaluation selon trois protocoles ;
  * `prediction`       : chargement du modèle et usage en production.
"""
