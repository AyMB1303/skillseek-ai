#!/usr/bin/env bash
#
# Demarrage de SkillSeek AI dans un Codespace.
#
# La difficulte que ce script resout tient en une phrase : dans un Codespace,
# le navigateur n'est PAS sur la machine qui execute l'application. Les deux
# communiquent par des adresses publiques que GitHub attribue au demarrage,
# de la forme https://<nom-du-codespace>-<port>.<domaine>.
#
# Consequence : `http://localhost:5000/api`, qui fonctionne sur un poste de
# developpement, ne designe plus rien pour le navigateur d'un Codespace. Le
# frontend appellerait dans le vide et l'interface resterait muette. Ce script
# calcule donc les deux adresses et les inscrit dans `.env` avant tout
# demarrage — l'une pour que le navigateur trouve l'API, l'autre pour que
# l'API accepte les appels du navigateur (politique CORS).

set -euo pipefail

cd "$(dirname "$0")/.."

echo "→ Configuration"

if [ ! -f .env ]; then
  cp .env.example .env
fi

if [ -n "${CODESPACE_NAME:-}" ]; then
  domaine="${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  url_api="https://${CODESPACE_NAME}-5000.${domaine}/api"
  url_interface="https://${CODESPACE_NAME}-3000.${domaine}"

  # Les lignes existantes sont retirees avant d'etre reecrites : relancer ce
  # script ne doit pas empiler les doublons dans le fichier.
  sed -i '/^NEXT_PUBLIC_API_URL=/d;/^FRONTEND_ORIGIN=/d' .env
  {
    echo "NEXT_PUBLIC_API_URL=${url_api}"
    echo "FRONTEND_ORIGIN=${url_interface}"
  } >> .env

  echo "   API       : ${url_api}"
  echo "   Interface : ${url_interface}"
else
  echo "   Hors Codespace : configuration locale conservee."
fi

echo "→ Construction des images (plusieurs minutes la premiere fois)"
docker compose up -d --build

echo "→ Attente de la base de donnees"
for _ in $(seq 1 60); do
  if docker compose exec -T db pg_isready -q 2>/dev/null; then break; fi
  sleep 2
done

echo "→ Schema et donnees"
docker compose exec -T backend flask db upgrade
docker compose exec -T backend flask seed
docker compose exec -T backend flask demo --reset

echo "→ Attente de l'API"
for _ in $(seq 1 60); do
  if curl -fsS http://localhost:5000/api/health >/dev/null 2>&1; then break; fi
  sleep 2
done

cat <<'FIN'

────────────────────────────────────────────────────────────
  SkillSeek AI est demarre.

  Ouvrez l'onglet « Ports » et cliquez sur le port 3000.

  Candidat        y.tazi@example.ma        Demo@1234
  Recruteur       s.lamrani@bcskills.ma    Demo@1234
  Administrateur  admin@skillseek.local    Admin@1234
────────────────────────────────────────────────────────────

FIN
