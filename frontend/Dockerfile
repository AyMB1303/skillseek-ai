# Image de production du frontend, construite en trois etapes.
#
# L'interet du decoupage n'est pas cosmetique. Chaque instruction produit une
# couche mise en cache : en installant les dependances AVANT de copier le code,
# une modification d'un composant ne reinstalle pas les paquets. Et seule la
# derniere etape devient l'image finale — ni les sources, ni les outils de
# construction, ni le cache npm n'y figurent.

# --- 1. Dependances -----------------------------------------------------
FROM node:26-alpine AS dependances
WORKDIR /app

# `npm ci` plutot que `npm install` : l'installation suit exactement le fichier
# de verrouillage, donc l'image construite aujourd'hui contient les memes
# versions que celle construite dans six mois.
COPY package.json package-lock.json* ./
RUN npm ci

# --- 2. Construction ----------------------------------------------------
FROM node:26-alpine AS constructeur
WORKDIR /app

# L'adresse de l'API est inscrite dans le bundle navigateur au moment de la
# construction : elle doit donc arriver ici, et non au demarrage.
ARG NEXT_PUBLIC_API_URL=http://localhost:5000/api
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=dependances /app/node_modules ./node_modules
COPY . .
RUN npm run build

# --- 3. Execution -------------------------------------------------------
FROM node:26-alpine AS execution
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000

# Compte sans privileges : un processus compromis ne doit pas etre root dans
# le conteneur.
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# `public/` héberge les fichiers servis tels quels — favicon, images, robots.txt.
# Le dossier est actuellement vide (un `.gitkeep` l'y maintient) mais la copie
# est conservée : Next l'attend, et le premier fichier ajouté fonctionnera sans
# qu'il faille penser à modifier ce Dockerfile.
COPY --from=constructeur /app/public ./public
COPY --from=constructeur --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=constructeur --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

# Sonde de vie : Docker sait alors distinguer un conteneur demarre d'un
# conteneur qui repond reellement.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
