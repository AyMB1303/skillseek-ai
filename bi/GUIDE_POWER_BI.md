# Rapports décisionnels Power BI — SkillSeek AI

Ce document décrit la mise en place des deux rapports prévus au cahier des
charges : une vue **recruteur**, centrée sur le pilotage quotidien, et une vue
**direction**, centrée sur les volumes et l'efficacité du dispositif.

---

## 1. Préparer les données

Une seule commande crée la couche décisionnelle dans PostgreSQL :

```
docker compose exec backend flask bi-creer-vues
```

Six vues sont créées. Elles constituent le **contrat** entre la base et le
rapport : le vocabulaire métier y est fixé en français, et les règles de
gestion — seuil de présélection à 50 points, exclusion de la corbeille — y
sont appliquées une fois pour toutes. Aucun visuel Power BI ne doit donc
réimplémenter une règle : si le seuil change un jour, il change ici seulement.

| Vue | Contenu | Granularité |
|---|---|---|
| `bi_indicateurs` | Indicateurs de synthèse | une seule ligne |
| `bi_candidatures` | Table de faits principale | une candidature |
| `bi_offres` | Référentiel des offres | une offre |
| `bi_entonnoir` | Étapes du recrutement et conversions | une étape |
| `bi_activite` | Volumes et note moyenne | un jour |
| `bi_competences` | Compétences demandées | une compétence |

Aucune donnée personnelle n'y figure au-delà du nécessaire : le décisionnel
travaille sur des volumes et des délais, pas sur des individus. Ni adresse
électronique, ni numéro de téléphone, ni nom de candidat.

---

## 2. Se connecter depuis Power BI

### Voie normale — connexion directe à PostgreSQL

**Obtenir les données → Base de données PostgreSQL**

| Champ | Valeur |
|---|---|
| Serveur | `localhost:5432` |
| Base de données | celle définie par `POSTGRES_DB` dans votre `.env` |
| Mode | Import |
| Identifiants | ceux de `POSTGRES_USER` / `POSTGRES_PASSWORD` |

Sélectionnez les six vues `bi_*`. Le mode Import charge une copie des données
dans le rapport ; un clic sur *Actualiser* la met à jour.

> Si Power BI réclame le pilote **Npgsql**, installez-le depuis
> `github.com/npgsql/npgsql/releases` (paquet *GAC*), puis relancez Power BI.
> Si son installation est impossible sur votre poste, utilisez la voie
> suivante.

### Voie de secours — fichiers CSV

```
docker compose exec backend flask bi-export
```

Six fichiers apparaissent dans le dossier `exports/` du projet. Dans Power BI :
**Obtenir les données → Texte/CSV**, séparateur **point-virgule**, encodage
**UTF-8**.

Les fichiers reproduisent exactement les colonnes des vues : un rapport
construit sur les fichiers peut être rebasculé sur la connexion directe sans
être refait.

---

## 3. Modèle de données

Une seule relation à créer dans la vue *Modèle* :

```
bi_offres[offre_id]  1 ──────< *  bi_candidatures[offre_id]
```

Cardinalité **un à plusieurs**, sens de filtre **simple**, de `bi_offres` vers
`bi_candidatures`. Les autres tables sont indépendantes et alimentent leurs
propres visuels.

---

## 4. Mesures DAX

À créer dans la table `bi_candidatures` (*Nouvelle mesure*).

```dax
Candidatures = COUNTROWS(bi_candidatures)

Retenues =
CALCULATE([Candidatures], bi_candidatures[qualification] = "Retenue")

Taux de présélection =
DIVIDE([Retenues], [Candidatures])

Note moyenne =
AVERAGE(bi_candidatures[note])

Entretiens =
CALCULATE([Candidatures], bi_candidatures[statut] = "Entretien")

Recrutements =
CALCULATE([Candidatures], bi_candidatures[statut] = "Recrutée")

Taux de transformation =
DIVIDE([Recrutements], [Entretiens])

En attente =
CALCULATE([Candidatures], bi_candidatures[statut] IN {"Reçue", "En étude"})

Délai moyen de traitement =
AVERAGE(bi_candidatures[jours_en_attente])

Candidatures analysées =
CALCULATE([Candidatures], NOT ISBLANK(bi_candidatures[note]))

Taux d'analyse automatique =
DIVIDE([Candidatures analysées], [Candidatures])
```

Formatez *Taux de présélection*, *Taux de transformation* et *Taux d'analyse
automatique* en pourcentage à une décimale.

---

## 5. Rapport 1 — Vue recruteur

Destinataire : le recruteur, quotidiennement. Question à laquelle la page doit
répondre en un coup d'œil : **que dois-je traiter aujourd'hui ?**

**Bandeau de cartes**, en haut :
`Candidatures` · `Retenues` · `En attente` · `Délai moyen de traitement`

**Entonnoir** — visuel *Entonnoir*, source `bi_entonnoir` :
catégorie `etape`, valeur `volume`, tri par `rang` croissant.

**Répartition des notes** — histogramme, source `bi_candidatures` :
axe `tranche_de_note`, valeur `Candidatures`. Ordonnez l'axe manuellement :
`Moins de 30`, `30 à 49`, `50 à 69`, `70 à 84`, `85 et plus`, `Sans note`.

**Candidatures par offre** — tableau, source `bi_candidatures` :
colonnes `intitule_offre`, `Candidatures`, `Retenues`, `Note moyenne`,
`Entretiens`. Ajoutez une mise en forme conditionnelle par barres de données
sur *Note moyenne*.

**Activité** — courbe, source `bi_activite` : axe `jour`, valeurs
`candidatures` et `retenues`.

**Segments**, dans un volet latéral : `type_contrat`, `localisation`,
`statut`.

---

## 6. Rapport 2 — Vue direction

Destinataire : la direction, mensuellement. Question : **le dispositif
fonctionne-t-il, et où sont les tensions ?**

**Bandeau de cartes** :
`Offres` · `Candidatures` · `Taux de présélection` · `Taux de transformation`
· `Taux d'analyse automatique`

**Attractivité des offres** — barres horizontales, source `bi_candidatures` :
axe `intitule_offre`, valeur `Candidatures`, tri décroissant. Fait apparaître
les offres qui ne recrutent pas faute de candidats.

**Qualité des candidatures reçues** — barres empilées :
axe `intitule_offre`, légende `qualification`, valeur `Candidatures`. Une
offre dont la barre est majoritairement « Écartée » signale un décalage entre
l'annonce et le marché.

**Compétences les plus demandées** — barres, source `bi_competences` :
axe `competence`, valeur `nb_offres`, légende `nature`.

**Efficacité de l'analyse automatique** — anneau, source `bi_candidatures` :
légende `methode_extraction`, valeur `Candidatures`. Montre la part de CV
ayant nécessité la reconnaissance optique.

**Évolution mensuelle** — courbe : axe `mois`, valeurs `Candidatures` et
`Note moyenne` sur un second axe.

---

## 7. Ce que ces rapports permettent de dire

Trois lectures qu'un tableau de bord applicatif ne donne pas :

**Le décalage entre une annonce et le marché.** Une offre dont la grande
majorité des candidatures sont écartées ne souffre pas d'un défaut de
sourcing : ses exigences sont probablement mal calibrées. Le visuel de qualité
par offre le rend immédiatement visible.

**Le goulot d'étranglement du processus.** L'entonnoir situe la perte : entre
la réception et la présélection, c'est un problème d'attractivité ; entre la
présélection et l'entretien, c'est un problème de disponibilité du recruteur.

**Le coût caché des CV mal formés.** La part de documents traités par
reconnaissance optique, et celle des candidatures sans note, mesurent ce que
la plateforme ne parvient pas à automatiser.

---

## 8. Actualisation

En mode Import, les données sont figées au moment du chargement. *Accueil →
Actualiser* les met à jour. Une actualisation planifiée suppose une passerelle
Power BI et une base accessible depuis le service, ce qui sort du périmètre
d'une installation locale.
