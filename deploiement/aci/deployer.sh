#!/usr/bin/env bash
#
# Deploiement de SkillSeek AI sur Azure Container Instances.
#
# A executer depuis le Cloud Shell Azure :
#
#   git clone --depth 1 https://github.com/AyMB1303/skillseek-ai.git
#   cd skillseek-ai
#   bash deploiement/aci/deployer.sh
#
# Pourquoi ACI plutot qu'une machine virtuelle : l'abonnement academique
# utilise n'accorde aucun quota de processeurs virtuels sur les familles de
# machines proposees dans les regions autorisees. Les conteneurs relevent
# d'un quota distinct, disponible lui.
#
# Ce que le script produit : un groupe de quatre conteneurs — base de
# donnees, service applicatif, interface, proxy — partageant une pile reseau
# et une adresse publique. C'est la transposition directe de
# `docker-compose.prod.yml`, aux deux differences pres que la configuration
# nginx vise `127.0.0.1` et que les migrations se lancent au demarrage.

set -euo pipefail

GROUPE="${GROUPE:-SkillSeek-demo}"
REGION="${REGION:-germanywestcentral}"
NOM="${NOM:-skillseek}"
DEPOT="${DEPOT:-aymb1303/skillseek-ai}"   # minuscules : GHCR l'impose
ETIQUETTE="${ETIQUETTE:-latest}"

# Etiquette DNS : doit etre unique dans la region. Un suffixe aleatoire evite
# la collision avec un groupe cree precedemment et non encore libere.
DNS="${DNS:-skillseek-$(head -c 3 /dev/urandom | od -An -tx1 | tr -d ' \n')}"

racine="$(cd "$(dirname "$0")/../.." && pwd)"

echo "→ Secrets de session"
# Trois secrets neufs a chaque deploiement. Ceux de `.env.example` sont
# publics dans le depot : les reprendre sur une machine exposee reviendrait a
# publier les cles de signature des jetons.
MDP_BASE="$(openssl rand -hex 24)"
CLE_SECRETE="$(openssl rand -hex 32)"
CLE_JWT="$(openssl rand -hex 32)"

echo "→ Configuration du proxy"
NGINX_B64="$(base64 -w0 "$racine/deploiement/aci/nginx.conf")"

FQDN="${DNS}.${REGION}.azurecontainer.io"
echo "   adresse prevue : http://${FQDN}"

# Le service applicatif attend la base, applique les migrations, installe les
# roles puis le jeu de demonstration, et seulement ensuite se met a ecouter.
# Sans la boucle d'attente, la premiere migration echouerait : dans un groupe
# ACI les conteneurs demarrent ensemble, sans ordre garanti.
LANCEMENT='for i in $(seq 1 90); do python -c "import socket; socket.create_connection((\"127.0.0.1\", 5432), 2)" 2>/dev/null && break; sleep 2; done; flask db upgrade && flask seed && flask demo --reset; exec flask run --host=0.0.0.0 --port=5000'

echo "→ Description du groupe"
cat > /tmp/skillseek-aci.yaml <<YAML
apiVersion: 2021-10-01
location: ${REGION}
name: ${NOM}
properties:
  osType: Linux
  restartPolicy: OnFailure
  ipAddress:
    type: Public
    dnsNameLabel: ${DNS}
    ports:
      - protocol: tcp
        port: 80
  volumes:
    - name: configuration-proxy
      secret:
        default.conf: ${NGINX_B64}
  containers:
    - name: db
      properties:
        image: postgres:16-alpine
        environmentVariables:
          - name: POSTGRES_USER
            value: skillseek
          - name: POSTGRES_PASSWORD
            secureValue: ${MDP_BASE}
          - name: POSTGRES_DB
            value: skillseek
          - name: PGDATA
            value: /var/lib/postgresql/data/pgdata
        resources:
          requests:
            cpu: 0.5
            memoryInGB: 1.5

    - name: backend
      properties:
        image: ghcr.io/${DEPOT}/backend:${ETIQUETTE}
        command:
          - /bin/sh
          - -c
          - ${LANCEMENT@Q}
        environmentVariables:
          - name: DATABASE_URL
            secureValue: postgresql://skillseek:${MDP_BASE}@127.0.0.1:5432/skillseek
          - name: SECRET_KEY
            secureValue: ${CLE_SECRETE}
          - name: JWT_SECRET_KEY
            secureValue: ${CLE_JWT}
          - name: FLASK_ENV
            value: production
          # Pas de FLASK_APP : depuis /app, Flask decouvre seul le paquet
          # `app` et sa fabrique `create_app`. Designer un fichier inexistant
          # ferait echouer le demarrage.
          - name: FRONTEND_ORIGIN
            value: http://${FQDN}
          - name: GIT_SHA
            value: ${ETIQUETTE}
          - name: LOGIN_MAX_ECHECS
            value: "5"
          - name: LOGIN_VERROU_MINUTES
            value: "10"
        resources:
          requests:
            cpu: 2.0
            memoryInGB: 8.0

    - name: frontend
      properties:
        image: ghcr.io/${DEPOT}/frontend:${ETIQUETTE}
        environmentVariables:
          - name: PORT
            value: "3000"
          - name: HOSTNAME
            value: 0.0.0.0
        resources:
          requests:
            cpu: 0.5
            memoryInGB: 1.5

    - name: proxy
      properties:
        image: nginx:1.27-alpine
        ports:
          - protocol: tcp
            port: 80
        volumeMounts:
          - name: configuration-proxy
            mountPath: /etc/nginx/conf.d
        resources:
          requests:
            cpu: 0.5
            memoryInGB: 1.0
YAML

echo "→ Création du groupe (plusieurs minutes : l'image backend pèse 3,7 Go)"
az container create --resource-group "${GROUPE}" --file /tmp/skillseek-aci.yaml --output none

echo ""
echo "────────────────────────────────────────────────────────────"
echo "  Adresse : http://${FQDN}"
echo ""
echo "  Le service applicatif applique les migrations et charge le"
echo "  jeu de démonstration avant de répondre. Comptez trois à cinq"
echo "  minutes après la fin de cette commande."
echo ""
echo "  Suivre le démarrage :"
echo "    az container logs -g ${GROUPE} -n ${NOM} --container-name backend --follow"
echo ""
echo "  Comptes :"
echo "    y.tazi@example.ma        Demo@1234"
echo "    s.lamrani@bcskills.ma    Demo@1234"
echo "    admin@skillseek.local    Admin@1234"
echo ""
echo "  Libérer les ressources une fois les captures prises :"
echo "    az group delete --name ${GROUPE} --yes"
echo "────────────────────────────────────────────────────────────"
