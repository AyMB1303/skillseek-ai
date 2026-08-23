# Déploiement sur Azure — procédure complète

Objectif : mettre SkillSeek AI en ligne sur une machine Azure, et activer le
déploiement automatique depuis GitHub.

**Durée : 2 à 3 heures.** Six étapes. Ne saute aucune, et va jusqu'au bout
d'une étape avant d'attaquer la suivante.

Remplace partout `<IP>` par l'adresse publique de ta machine.

---

## Étape 0 — Publier les images

Le serveur ne construit rien : il **télécharge** les images produites par la
chaîne d'intégration. Or celles-ci ne sont publiées que sur `main`.

```bash
git checkout main
git merge dev
git push origin main
```

Va dans l'onglet **Actions** et attends que l'exécution se termine — une
quinzaine de minutes, la construction du backend étant longue.

Vérifie ensuite dans **ton profil GitHub → Packages** que `backend` et
`frontend` apparaissent.

---

## Étape 1 — Créer la machine

Portail Azure → **Créer une ressource → Machine virtuelle**.

| Réglage | Valeur |
|---|---|
| Image | Ubuntu Server 24.04 LTS |
| Taille | **B2s** (2 vCPU, 4 Go) |
| Région | France Central ou West Europe |
| Authentification | Clé publique SSH, générer une nouvelle paire |
| Nom d'utilisateur | `azureuser` |
| Ports entrants | **22 (SSH) et 80 (HTTP)** |
| Disque | Standard SSD, 30 Go |

Azure fait télécharger la **clé privée** à la création. Elle n'est
téléchargeable qu'une fois. Range-la, ne la partage avec personne.

> **Pourquoi seulement 22 et 80 ?** Un proxy publie l'interface et l'API sur
> le port 80. Ouvrir 3000 et 5000 offrirait un second chemin vers les services,
> échappant aux limites de taille et de délai posées par le proxy.

Note l'**adresse IP publique** affichée après la création.

---

## Étape 2 — Préparer le serveur

Depuis ton poste :

```bash
ssh -i chemin/vers/cle.pem azureuser@<IP>
```

Puis, sur le serveur :

```bash
# Docker, depuis le script officiel
curl -fsSL https://get.docker.com | sudo sh

# Pouvoir lancer docker sans sudo
sudo usermod -aG docker azureuser

# Le dossier de déploiement
sudo mkdir -p /opt/skillseek
sudo chown azureuser:azureuser /opt/skillseek
```

**Déconnecte-toi et reconnecte-toi** — l'appartenance au groupe `docker` ne
prend effet qu'à l'ouverture de session suivante.

```bash
exit
ssh -i chemin/vers/cle.pem azureuser@<IP>
docker run --rm hello-world     # doit réussir sans sudo
```

---

## Étape 3 — Rendre les images publiques

Par défaut les paquets GHCR sont privés, et le serveur ne pourrait pas les
récupérer.

Pour **chacune** des deux images (`backend` et `frontend`) :

GitHub → ton profil → **Packages** → le paquet → **Package settings** →
*Danger Zone* → **Change visibility** → **Public**.

> Alternative si tu préfères les garder privées : créer un jeton d'accès
> personnel avec la portée `read:packages` et faire `docker login ghcr.io`
> sur le serveur. Plus sûr, mais un secret de plus à gérer. Pour un projet
> pédagogique dont le code est déjà public, la visibilité publique est
> cohérente.

---

## Étape 4 — Les fichiers sur le serveur

Sur le serveur :

```bash
cd /opt/skillseek
git clone --depth 1 https://github.com/AyMB1303/skillseek-ai.git depot
cp depot/docker-compose.prod.yml .
mkdir -p deploiement && cp depot/deploiement/nginx.conf deploiement/
mkdir -p models
rm -rf depot
```

Génère trois secrets **neufs** :

```bash
openssl rand -hex 32   # à faire trois fois
```

Crée `/opt/skillseek/.env` avec `nano .env` :

```bash
POSTGRES_USER=skillseek
POSTGRES_PASSWORD=<premier secret>
POSTGRES_DB=skillseek
DATABASE_URL=postgresql://skillseek:<premier secret>@db:5432/skillseek

SECRET_KEY=<deuxième secret>
JWT_SECRET_KEY=<troisième secret>
FLASK_ENV=production

FRONTEND_ORIGIN=http://<IP>

GITHUB_REPOSITORY=AyMB1303/skillseek-ai
IMAGE_TAG=latest

LOGIN_MAX_ECHECS=5
LOGIN_VERROU_MINUTES=10
```

> **Jamais les valeurs de `.env.example`.** Elles sont publiques dans ton
> dépôt : les réutiliser sur une machine exposée reviendrait à publier tes
> clés de session.

> `NEXT_PUBLIC_API_URL` n'y figure pas, et c'est normal : l'image frontend
> embarque le chemin relatif `/api`, que le proxy route vers le service
> applicatif.

Premier démarrage :

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec -T backend flask db upgrade
docker compose -f docker-compose.prod.yml exec -T backend flask seed
docker compose -f docker-compose.prod.yml exec -T backend flask demo --reset
```

Ouvre **http://\<IP\>** dans ton navigateur. La plateforme doit répondre.

Si elle ne répond pas :

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend --tail 50
docker compose -f docker-compose.prod.yml logs proxy --tail 20
```

---

## Étape 5 — Activer le déploiement automatique

Dépôt GitHub → **Settings → Secrets and variables → Actions → New repository
secret**. Quatre secrets :

| Nom | Valeur |
|---|---|
| `SSH_HOTE` | `<IP>` |
| `SSH_UTILISATEUR` | `azureuser` |
| `SSH_CLE_PRIVEE` | le **contenu entier** du fichier de clé privée, lignes `BEGIN` et `END` comprises |
| `CHEMIN_DEPLOIEMENT` | `/opt/skillseek` |

Puis : onglet **Actions → Déploiement → Run workflow**, version `latest`,
cible `staging`.

Le workflow se connecte en SSH, récupère les images, applique les migrations,
interroge `/api/ready`, et **revient tout seul à la version précédente** si le
service ne répond pas.

---

## Étape 6 — Éteindre

**Toujours par le portail Azure**, bouton *Stop*. L'état doit afficher
**« Stopped (deallocated) »**.

`sudo shutdown` depuis SSH laisse la machine en *Stopped* tout court : Azure
te réserve les ressources et continue de les facturer.

| | Coût mensuel |
|---|---|
| B2s en fonctionnement continu | ~30 $ |
| B2s arrêtée (deallocated) | ~2–3 $, le disque seul |

Avec 100 $ de crédit et un usage limité aux démonstrations, la machine tient
jusqu'à l'expiration du crédit.

---

## Avant la soutenance

Rallume la machine la veille, pas le jour même : l'adresse IP publique change
à chaque redémarrage si elle est dynamique, et le secret `SSH_HOTE` doit alors
être corrigé.

Vérifie dans l'ordre : `http://<IP>` répond, la connexion fonctionne avec les
trois comptes, et une analyse de CV aboutit.

**Prends une capture d'écran de la plateforme en ligne avec son URL visible.**
Elle prouve que la chaîne va du commit jusqu'au service en fonctionnement —
c'est la preuve que ton rapport ne pouvait pas fournir jusqu'ici.
