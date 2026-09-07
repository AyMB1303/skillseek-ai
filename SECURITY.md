# Politique de sécurité

## Portée

SkillSeek AI est un projet réalisé dans le cadre d'un stage de fin d'année. Il
n'est pas exploité en production et ne traite aucune donnée personnelle réelle :
le jeu de démonstration est fabriqué, et les curriculums qu'il contient ne
désignent personne.

Cela ne dispense pas de traiter les signalements sérieusement — un défaut
trouvé ici serait vraisemblablement présent dans un logiciel du même type qui,
lui, traiterait de vraies candidatures.

## Versions couvertes

| Version | Suivie |
|---|---|
| `main` | oui |
| étiquettes antérieures à la dernière | non |

Seule la branche principale reçoit des correctifs. Une étiquette publiée n'est
pas maintenue : elle fige un état, elle ne le suit pas.

## Signaler une vulnérabilité

Ouvrez un signalement privé ici :
<https://github.com/AyMB1303/skillseek-ai/security/advisories/new>

Ce canal n'est pas public : le défaut n'est visible que de vous et de moi tant
qu'il n'est pas corrigé. **N'ouvrez pas d'*issue* publique** pour un problème
de sécurité — elle serait lisible de tous avant qu'un correctif existe.

Précisez si possible l'empreinte du commit concerné, les étapes qui
reproduisent le comportement, et ce que le défaut permet d'obtenir.

**Ce à quoi je m'engage :**

| Étape | Délai |
|---|---|
| Accusé de réception | 5 jours |
| Première évaluation, et gravité retenue | 10 jours |
| Correctif ou explication motivée de l'absence de correctif | 30 jours |
| Publication du constat, une fois le correctif diffusé | 90 jours |

Ces délais sont ceux d'un projet tenu par une seule personne. Si un défaut est
activement exploité, écrivez-le en toutes lettres dans le signalement : il
passe alors avant tout le reste.

## Ce qui est déjà vérifié automatiquement

Chaque modification poussée déclenche six contrôles, chacun répondant à une
question que les autres ne posent pas :

| Contrôle | Ce qu'il cherche |
|---|---|
| **Gitleaks** | Un secret dans l'historique Git — y compris dans un commit dont le fichier a depuis été supprimé |
| **Trivy** (dépôt, configuration, images) | Une dépendance ou une image portant une vulnérabilité connue, une configuration de conteneur permissive |
| **Bandit** | Un motif dangereux dans le code Python |
| **Semgrep** | Un motif dangereux indépendant du langage |
| **CodeQL** | Un chemin d'exécution vulnérable, par analyse du flot de données |
| **OWASP ZAP** | Un défaut visible seulement sur l'application en marche |

Les constats sont publiés dans l'onglet **Security** du dépôt. La recherche de
secrets est bloquante : une modification qui en introduit un n'est pas
fusionnée.

## Ce qui n'est pas couvert

- Les manifestes Kubernetes sont validés et analysés, mais le cluster de
  démonstration n'est pas maintenu en ligne : aucun correctif d'exploitation
  n'y est appliqué.
- L'environnement de démonstration expose des comptes dont les mots de passe
  sont publics et documentés comme tels. Ils n'ouvrent qu'une base jetable.
- La politique de sécurité du contenu appliquée par le navigateur reste
  permissive sur les scripts et styles déposés en ligne dans la page. C'est une
  limite assumée, énoncée dans le rapport du projet.
