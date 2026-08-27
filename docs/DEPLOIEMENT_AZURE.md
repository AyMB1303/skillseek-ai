# Déploiement sur Azure — session de validation

Objectif : mettre SkillSeek AI en ligne le temps d'une session, **prouver que
la chaîne de déploiement fonctionne de bout en bout**, prendre les captures qui
en attestent, puis libérer les ressources.

**Durée : 2 à 3 heures. Coût : environ 1 $** de crédit académique.

La plateforme n'a pas vocation à rester en ligne. Ce qui est démontré ici, ce
n'est pas l'hébergement — c'est que le commit va jusqu'au service en
fonctionnement, sans intervention manuelle.

Remplace partout `<IP>` par l'adresse publique de ta machine.

---

## Avant de commencer

Une seule règle sur le choix de la machine : **prends la première taille que la
validation Azure accepte.** Le prix mensuel affiché n'a aucune importance — sur
trois heures, une machine à 78 $/mois coûte 32 centimes. Ne perds pas de temps
à chercher la moins chère.

---

## Étape 0 — Publier les images

Le serveur ne construit rien, il télécharge. Or les images ne sont publiées au
registre que depuis `main`, et `dev` a six commits d'avance.

```bash
git checkout main
git merge dev
git push origin main
```

Onglet **Actions** → attends la fin de l'exécution. Une quinzaine de minutes,
la construction du backend étant longue.

Vérifie ensuite dans **ton profil GitHub → Packages** que `backend` et
`frontend` apparaissent.

```bash
git checkout dev      # revenir sur la branche de travail
```

---

## Étape 1 — Créer la machine

Portail Azure → **Créer une ressource → Machine virtuelle**.

| Réglage | Valeur |
|---|---|
| Groupe de ressources | **`SkillSeek-demo`** — nom dédié, il sera supprimé en entier à l'étape 7 |
| **Region** | **`(Europe) Germany West Central`** |
| Image | **Ubuntu Server 24.04 LTS** — surtout pas « Pro », qui est payant |
| **Size** | **`Standard_D2s_v7`** — 2 vCPU, 8 Go, x86 |
| Availability options | *No infrastructure redundancy required* |
| Security type | `Standard` |
| Authentification | Clé publique SSH, générer une nouvelle paire |
| Nom d'utilisateur | `azureuser` |
| Ports entrants | **22 (SSH) et 80 (HTTP)** |
| Disque | Standard SSD |

> **La région n'est pas négociable.** L'abonnement porte une politique
> « Allowed resource deployment regions » qui n'en autorise que cinq :
> `polandcentral`, `germanywestcentral`, `switzerlandnorth`, `swedencentral`,
> `austriaeast`. Toute autre région est refusée à la validation, sans que le
> portail le signale au moment du choix. Germany West Central est la plus
> proche du Maroc.
>
> **Éviter toute taille contenant un `p`** — `D2ps_v6`, `D2pds_v6` et
> semblables sont des machines **ARM**. Les images du projet sont construites
> pour x86 et n'y démarreraient pas.

Azure fait télécharger la **clé privée** à la création — une seule fois. Range-la,
ne la partage avec personne.

Note l'**adresse IP publique** affichée après la création.

---

## Étape 2 — Préparer le serveur

```bash
ssh -i chemin/vers/cle.pem azureuser@<IP>
```

Sur le serveur :

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker azureuser
sudo mkdir -p /opt/skillseek
sudo chown azureuser:azureuser /opt/skillseek
```

**Déconnecte-toi et reconnecte-toi** — l'appartenance au groupe `docker` ne
prend effet qu'à la session suivante.

```bash
exit
ssh -i chemin/vers/cle.pem azureuser@<IP>
docker run --rm hello-world      # doit réussir sans sudo
```

---

## Étape 3 — Rendre les images publiques

Sinon le serveur ne pourra pas les télécharger.

Pour **chacune** des deux images : GitHub → ton profil → **Packages** → le
paquet → **Package settings** → *Danger Zone* → **Change visibility** →
**Public**.

---

## Étape 4 — Premier démarrage

Sur le serveur :

```bash
cd /opt/skillseek
git clone --depth 1 https://github.com/AyMB1303/skillseek-ai.git depot
cp depot/docker-compose.prod.yml .
mkdir -p deploiement models
cp depot/deploiement/nginx.conf deploiement/
rm -rf depot

openssl rand -hex 32      # trois fois, note les trois valeurs
nano .env
```

Contenu de `.env` :

```bash
POSTGRES_USER=skillseek
POSTGRES_PASSWORD=<secret 1>
POSTGRES_DB=skillseek
DATABASE_URL=postgresql://skillseek:<secret 1>@db:5432/skillseek

SECRET_KEY=<secret 2>
JWT_SECRET_KEY=<secret 3>
FLASK_ENV=production

FRONTEND_ORIGIN=http://<IP>

GITHUB_REPOSITORY=AyMB1303/skillseek-ai
IMAGE_TAG=latest

LOGIN_MAX_ECHECS=5
LOGIN_VERROU_MINUTES=10
```

> **Jamais les valeurs de `.env.example`** — elles sont publiques dans le dépôt.

Démarrage :

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec -T backend flask db upgrade
docker compose -f docker-compose.prod.yml exec -T backend flask seed
docker compose -f docker-compose.prod.yml exec -T backend flask demo --reset
```

Ouvre **http://\<IP\>**. La plateforme doit répondre.

En cas de problème :

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend --tail 50
docker compose -f docker-compose.prod.yml logs proxy --tail 20
```

---

## Étape 5 — Déclencher le déploiement automatique

C'est cette étape qui produit la preuve la plus importante : non pas qu'un
serveur existe, mais que **la chaîne y déploie toute seule**.

Dépôt GitHub → **Settings → Secrets and variables → Actions → New repository
secret**. Quatre secrets :

| Nom | Valeur |
|---|---|
| `SSH_HOTE` | `<IP>` |
| `SSH_UTILISATEUR` | `azureuser` |
| `SSH_CLE_PRIVEE` | le **contenu entier** du fichier de clé privée, lignes `BEGIN` et `END` comprises |
| `CHEMIN_DEPLOIEMENT` | `/opt/skillseek` |

Puis **Actions → Déploiement → Run workflow**, version `latest`, cible
`staging`.

Le workflow se connecte, récupère les images, applique les migrations,
interroge `/api/ready`, et reviendrait tout seul à la version précédente si le
service ne répondait pas.

---

## Étape 6 — Les captures

**C'est le vrai livrable de cette session.** Prends-les toutes avant de
supprimer quoi que ce soit.

1. **La plateforme en ligne, URL visible dans la barre d'adresse.** Connecté en
   recruteur, sur le détail d'une candidature analysée. Une seule image qui
   montre à la fois l'adresse publique et le produit qui fonctionne.
2. **Le workflow « Déploiement » au vert**, étapes déroulées. La preuve de
   l'automatisation.
3. **`docker compose -f docker-compose.prod.yml ps`** sur le serveur — les
   quatre conteneurs en vie.
4. **La page Azure de la machine**, comme preuve de l'infrastructure.
5. **`curl http://<IP>/api/ready`** depuis ton poste — les dépendances à `true`,
   interrogées depuis l'extérieur.

Range-les dans `docs/captures/`.

---

## Étape 7 — Tout supprimer

Portail Azure → **Groupes de ressources** → `SkillSeek-demo` → **Supprimer le
groupe de ressources**.

Supprimer le groupe entier emporte la machine, le disque, l'adresse IP, le
réseau et le groupe de sécurité d'un seul coup. Éteindre seulement la machine
laisserait le disque facturé à environ 2,40 $ par mois.

Vérifie ensuite dans **Cost Management** que la consommation s'est arrêtée.

---

## La formulation pour le rapport

Ne jamais écrire que la plateforme est « en production » — elle ne le sera plus
quand le jury lira.

> Le déploiement a été réalisé et vérifié sur une machine Azure : la chaîne se
> connecte au serveur, récupère les images publiées au registre, applique les
> migrations et contrôle la disponibilité du service. L'instance a été libérée
> après validation, le crédit académique disponible étant limité.

Exact, appuyé par les captures, et cohérent avec le reste du rapport. Libérer
une ressource inutilisée après validation est une décision d'ingénieur, pas un
aveu de faiblesse.
