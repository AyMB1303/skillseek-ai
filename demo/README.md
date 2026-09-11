# Enregistrement de la vidéo de démonstration

Le script pilote un vrai navigateur sur l'application réellement lancée et en
enregistre la vidéo. Rien n'est simulé : ce que la vidéo montre est ce que la
plateforme fait.

## Scénario

| | |
|---|---|
| Candidat | Sahri Zaid — le nom et l'adresse du compte sont ceux qui figurent sur le CV, faute de quoi le contrôle de cohérence ouvrirait un signalement |
| Offre | Développeur Full Stack — Stage (BC Skills, Rabat) |
| Recruteur | Sarah Lamrani — `s.lamrani@bcskills.ma`, propriétaire de l'offre |
| Note attendue | 67/100, aucun critère éliminatoire, une réserve |

La note n'est ni parfaite ni éliminatoire : c'est précisément le cas où
l'explication vaut quelque chose. La réserve relevée — « compétences citées
sans apparaître dans l'expérience décrite » — est le genre de nuance qu'un
moteur de mots-clés ne produit pas.

## Avant de lancer

1. La plateforme tourne : `docker compose up -d`
2. Le jeu de démonstration est en place : `docker compose exec backend flask demo`
   (c'est lui qui crée les offres et les comptes recruteurs)
3. Playwright est installé :

```powershell
cd "D:\Study stuff\SkillSeek"
npm install --no-save playwright
npx playwright install chromium
```

## Lancer

```powershell
node demo/enregistrer-demo.js
```

La vidéo arrive dans `demo/video/skillseek-demonstration.webm`.
Pour un MP4 — format attendu par la plupart des outils de présentation :

```powershell
ffmpeg -i demo/video/skillseek-demonstration.webm -c:v libx264 -crf 20 -pix_fmt yuv420p demo/video/skillseek-demonstration.mp4
```

## Réglages

| Variable | Rôle | Défaut |
|---|---|---|
| `SKILLSEEK_URL` | adresse du frontend | `http://localhost:3000` |
| `CV` | CV à déposer | `demo/Sahri_Zaid_CV.pdf` |
| `OFFRE` | intitulé de l'offre visée | `Développeur Full Stack — Stage` |
| `VISIBLE` | `0` pour enregistrer sans afficher la fenêtre | affichée |

```powershell
$env:OFFRE = "Data Scientist"; node demo/enregistrer-demo.js
```

## Notes

**La visite guidée est neutralisée** pendant l'enregistrement. Elle s'ouvre
d'elle-même à la première connexion d'un compte et son voile assombrit
l'écran. Le script la déclare vue au niveau du navigateur, sans toucher au
code de l'application — elle reste active pour les utilisateurs réels.

**Le compte candidat peut déjà exister** si la démonstration a déjà été jouée.
Le script poursuit alors par la connexion au lieu d'échouer. Pour repartir
d'une inscription vierge, supprimer le compte depuis l'espace administrateur,
ou rejouer `flask demo --reset`.

**En cas d'échec**, une capture de l'écran est déposée dans
`demo/video/echec.png` et le message d'erreur nomme l'étape.
