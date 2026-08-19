# Script d'enregistrement de la démonstration

Durée visée : **12 à 15 minutes**. Cinq séquences.

Le principe qui gouverne ce script : **ne jamais montrer un écran sans dire ce
qu'il prouve**. Un jury voit défiler des interfaces toute la journée ; ce dont
il se souvient, c'est d'une décision expliquée.

---

## Avant de lancer l'enregistrement

```bash
docker compose up -d
docker compose exec backend flask db upgrade
docker compose exec backend flask demo --reset
```

Une seule commande lève les trois services : `docker-compose.override.yml` est
chargé automatiquement et bascule le frontend en rechargement à chaud. Plus de
`npm run dev` séparé, et plus de conteneur figé servant une version périmée sur
le port 3000.

Le `--reset` est important : il régénère les candidatures **et** l'historique
du journal d'audit. Sans lui, l'écran d'audit serait vide.

**Vérifications, une minute :**

- `docker compose ps` → `db` et `backend` en vie
- `irm http://localhost:5000/api/ready` → `status: ready`, les trois
  dépendances à `True` (dont les deux modèles d'IA)
- Remplissez **trois grilles d'entretien** depuis le détail de candidatures en
  statut « Entretien ». Sans elles, la section la plus forte de la page Analyse
  affiche « aucune évaluation enregistrée ».

**Réglages d'écran :**

- Navigateur en plein écran, zoom à 100 %, onglets superflus fermés
- Thème sombre pour l'essentiel — basculez en clair trente secondes à la fin
  pour montrer que les deux existent
- Videz le stockage local si vous voulez que la visite guidée se déclenche
  (F12 → Application → Local storage → supprimer les clés `skillseek:visite:*`)

**Comptes :**

| Rôle | Identifiant | Mot de passe |
|---|---|---|
| Candidat | `y.tazi@example.ma` | `Demo@1234` |
| Recruteur | `s.lamrani@bcskills.ma` | `Demo@1234` |
| Administrateur | `admin@skillseek.local` | `Admin@1234` |

---

## Séquence 1 — Le candidat (2 min 30)

**Ce que ça prouve : le moteur fonctionne dans les deux sens.**

Connectez-vous en candidat. La **visite guidée** se déclenche — laissez-la
tourner deux ou trois étapes, puis passez. Dites simplement : « la plateforme
se présente elle-même à la première connexion ».

Allez sur **Offres pour moi**. Le formulaire est vide : saisissez trois ou
quatre compétences en montrant l'**autocomplétion** — tapez `js`, la plateforme
propose `javascript`. Précisez : *« ce référentiel est le même que celui qui lit
les CV et les offres ; une compétence saisie ici sera retrouvée à coup sûr »*.

Renseignez expérience et diplôme, enregistrez. Les offres se classent.

**Le point à faire, et c'est le plus important de la séquence :** montrez les
compétences manquantes sur une offre et dites — *« aucune note n'est affichée
au candidat. Un chiffre sans son barème invite au malentendu, et quelqu'un qui
aurait lu 87 % avant d'être écarté aurait un grief. On lui montre ce qui lui
manque, la seule chose qu'il puisse corriger. »*

Postulez à une offre. Puis **Mes candidatures** : le parcours de statuts,
sans score. Terminez en disant que le score reste interne au recruteur.

---

## Séquence 2 — Le recruteur, l'analyse d'un CV (4 min)

**Le cœur du projet. Prenez votre temps ici.**

Connectez-vous en recruteur. **Mes offres** d'abord : créez-en une pour montrer
la saisie de compétences par étiquettes et la **détection automatique depuis la
description**.

Puis **Candidatures**. Montrez la liste classée, les onglets RG-01 — Top 10,
Écartées, Sans score — et dites que rien n'est jamais supprimé : une
candidature écartée reste consultable et repêchable.

Ouvrez un dossier **bien noté**. Laissez le score monter, puis déroulez :

1. **Le détail du calcul** — les cinq composantes qui se révèlent une à une.
   Nommez les poids : compétences obligatoires 35, souhaitées 10, proximité
   sémantique 25, expérience 20, diplôme 10.
2. **La mise en correspondance** — survolez une exigence, sa contrepartie dans
   le CV s'éclaire. *« Le recruteur voit sur quoi le moteur s'est appuyé, et
   peut le contester. »*
3. **L'avis du modèle appris** — précisez qu'il ajuste de ±8 points au maximum
   et **ne peut jamais rattraper une candidature écartée par une règle**.

Ouvrez ensuite un dossier **écarté**. Montrez le motif exact. Dites : *« la
machine ne dit pas non, elle dit pourquoi — et le recruteur peut repêcher. »*

Si un dossier porte une **marque de vigilance**, ouvrez-le : le score reste
inchangé, seule une alerte s'ajoute. *« Fusionner l'adéquation et la fiabilité
dans un seul chiffre priverait le recruteur des deux signaux. »*

---

## Séquence 3 — Analyse et pilotage (3 min)

**Ce que ça prouve : le système accepte d'être jugé.**

Page **Analyse**. Parcourez dans l'ordre :

- Les repères, dont le **délai avant première décision** — précisez qu'il est
  lu dans le journal d'audit, la candidature ne portant pas de date de
  modification.
- La **répartition des notes**. Dites qu'une masse sous 50 signale une offre
  trop exigeante plus souvent qu'un vivier pauvre.
- **Ce qui écarte** et **les compétences absentes** — la lecture directe de
  l'écart entre ce qu'on demande et ce que le marché propose.

Puis **la section à ne pas manquer** : « Le classement tient-il ses promesses ? »

Arrêtez-vous sur **faux espoirs** et **pépites manquées**, et expliquez
pourquoi ils sont comptés séparément : *« un faux espoir coûte une heure
d'entretien ; une pépite manquée coûte un candidat, définitivement. »*

Phrase à placer : *« ce n'est pas une mesure sur un corpus public et
anglophone. C'est la note calculée avant l'entretien, confrontée au verdict
porté après, sur les candidats réellement reçus. Y compris quand l'écart est
défavorable au système. »*

Enchaînez sur le **Pipeline** (glisser une carte d'une colonne à l'autre) et
l'**Assistant RH** : posez deux questions en langage courant. *« Les chiffres
sont calculés en base, jamais reformulés par le modèle — c'est ce qui garantit
qu'ils sont exacts. »*

---

## Séquence 4 — Gouvernance (2 min 30)

**Ce que ça prouve : les droits sont réels, pas décoratifs.**

Connectez-vous en administrateur.

**Demandes recruteurs** : montrez le faisceau d'indices sur une demande —
nature du domaine, comptes déjà validés, ressemblance avec un domaine connu.
Dites que **rien n'est bloquant**, et pourquoi : *« refuser les adresses Gmail
écarterait les très petites entreprises sans gêner un fraudeur capable
d'acheter un domaine. »*

**Rôles et permissions** : la démonstration qui frappe. Retirez une permission
au rôle recruteur, basculez sur la fenêtre du recruteur, rafraîchissez —
l'accès est refusé **immédiatement**. *« Les permissions sont relues en base à
chaque requête sensible ; aucune attente d'expiration de session. »* Remettez
la permission.

**Journal d'audit** : filtrez par action. *« Les entrées sont immuables et
survivent à la suppression de l'objet visé — c'est souvent après une
suppression qu'on a besoin de savoir qui l'a ordonnée. »*

**L'assistant en vue administration** : demandez « combien de comptes attendent
une validation ? ». Point à faire : *« il ne restitue pas le contenu des
candidatures. Le rôle administrateur ne détient pas ce droit, et la
conversation ne doit pas contourner le modèle de permissions. »*

**La démonstration de sécurité qui vaut le détour** — si vous avez deux
minutes : connectez-vous avec le second recruteur (`m.bennani@technova.ma`) et
montrez qu'il ne voit **aucune** candidature de Sarah Lamrani.

---

## Séquence 5 — Industrialisation (2 min 30)

**Ce que ça prouve : c'est un produit, pas une maquette.**

Quittez le navigateur applicatif pour GitHub.

**Actions** → une exécution verte. Déroulez les six travaux : lint et tests
backend, lint et build frontend, audit des dépendances, analyse Trivy,
construction des deux images, démarrage de la pile complète. Ouvrez le journal
des tests pour montrer le compte réel.

**Packages** → les deux images publiées, étiquetées `latest` et `sha-…`.
*« Chaque commit produit un artefact déployable et identifiable. C'est ce qui
rend le retour arrière trivial : redémarrer avec l'étiquette précédente. »*

**Artifacts** d'une exécution → les inventaires SBOM. *« Quand une faille sort,
la question n'est pas si elle est grave mais si nous l'avons. »*

**Pull requests** → les propositions de Dependabot, dont celles rejetées par la
chaîne. *« Quatre montées de version majeure ont été arrêtées par les tests
avant d'atteindre le code. »*

Terminez sur un terminal :

```bash
docker compose ps
irm http://localhost:5000/api/ready
```

Et la phrase de clôture, à dire telle quelle : *« intégration et livraison
continues automatisées ; le déploiement vers un serveur est prêt mais non
activé, faute d'infrastructure dans le cadre du stage. »*

---

## Ce qu'il ne faut pas faire

**Ne pas prétendre au déploiement continu.** Vous avez de la livraison
continue. La distinction est nette et un jury la connaît.

**Ne pas présenter le modèle d'apprentissage comme le cœur du système.** C'est
un composant complémentaire, borné à ±8 points, incapable de contourner une
règle. La force du projet est la combinaison règles + sémantique + modèle +
explicabilité + décision humaine.

**Ne pas dire « sans biais ».** Dites que l'audit a mesuré au plus 2 points de
variation, attribuables à la similarité sémantique qui encode le document
entier, identité comprise. Négligeable mais réel.

**Ne rien montrer d'inachevé.** Pas de tests de bout en bout, pas de métriques
Prometheus, pas de serveur : mentionnez-les comme perspectives si on vous
interroge, ne les mettez pas à l'écran.

---

## Découpage des fichiers pour le partage

Un fichier par séquence plutôt qu'une seule vidéo : votre encadrant peut aller
directement à ce qui l'intéresse, et une erreur ne vous oblige à refaire qu'un
segment.

```
SkillSeek – Démonstration/
├── 1_candidat.mp4
├── 2_recruteur.mp4             ← la séquence à soigner
├── 3_administrateur.mp4
└── Rapport_Avancement_Sprint4.pdf
```

**Ce qui reste hors caméra avec trois fichiers.** Le découpage par rôle laisse
deux séquences sans support visuel : le **pilotage** (séquence 3 — écran
Analyse, faux espoirs et pépites manquées) et l'**industrialisation**
(séquence 5 — chaîne d'intégration, images publiées, inventaires logiciels).

La première se rattache naturellement à la vidéo recruteur, la seconde ne se
rattache à aucun rôle. Deux options, l'une et l'autre défendables : ajouter un
court `4_industrialisation.mp4` de deux minutes, ou traiter ce point à l'oral
en partageant l'écran sur GitHub le jour de la soutenance. La seconde a un
avantage réel — une chaîne d'intégration filmée paraît toujours moins vivante
qu'une exécution déclenchée devant le jury.

**Réglages d'enregistrement :** 1080p, 30 images par seconde, micro testé sur
trente secondes avant de commencer. OBS Studio ou l'enregistreur intégré de
Windows (`Win + Alt + R`) suffisent largement.

**Un conseil de fond :** parlez pendant que vous cliquez, pas après. Le silence
d'une interface qui charge est ce qui rend une démonstration longue.
