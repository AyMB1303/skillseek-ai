/**
 * Enregistrement vidéo du parcours de démonstration de SkillSeek AI.
 *
 * Le scénario est celui que la plateforme revendique, de bout en bout et sans
 * coupure : un candidat dépose son CV sur une offre, la plateforme l'analyse,
 * et le recruteur qui porte cette offre y retrouve une note, sa décomposition
 * et les réserves qui l'accompagnent. Le propos n'est pas de montrer un
 * classement — n'importe quel moteur de mots-clés en produit un — mais de
 * montrer qu'il est justifié : chaque point de la note renvoie à quelque chose
 * que l'on peut aller lire dans le document, affiché à côté.
 *
 * Le script pilote un vrai navigateur sur l'application réellement lancée. Il
 * ne simule rien : ce que la vidéo montre est ce que la plateforme fait.
 *
 *   node demo/enregistrer-demo.js
 *
 * Variables d'environnement acceptées :
 *   SKILLSEEK_URL   adresse du frontend            (défaut http://localhost:3000)
 *   CV              chemin du CV à déposer         (défaut demo/Sahri_Zaid_CV.pdf)
 *   OFFRE           intitulé de l'offre visée      (défaut « Développeur Full Stack — Stage »)
 *   VISIBLE         « 0 » pour enregistrer sans afficher la fenêtre
 */
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const BASE = (process.env.SKILLSEEK_URL || "http://localhost:3000").replace(/\/$/, "");
const CHEMIN_CV = process.env.CV || path.resolve(__dirname, "Sahri_Zaid_CV.pdf");
const OFFRE = process.env.OFFRE || "Développeur Full Stack — Stage";
const VISIBLE = process.env.VISIBLE !== "0";

const SORTIE = path.resolve(__dirname, "video");
const LARGEUR = 1440;
const HAUTEUR = 900;

// Le candidat porte le nom et l'adresse qui figurent sur le CV déposé. Ce
// n'est pas un détail de mise en scène : la plateforme compare les deux, et
// un écart ouvrirait un signalement — légitime, mais hors sujet ici.
const CANDIDAT = {
  nom: "Sahri Zaid",
  email: "sahrizaid8@gmail.com",
  motDePasse: "Demo@1234",
};

// Recruteur propriétaire de l'offre visée, tel que le jeu de démonstration le
// crée (`flask demo`). Les offres sont réparties à tour de rôle entre les
// recruteurs actifs ; celle du stage revient à BC Skills.
const RECRUTEUR = {
  nom: "Sarah Lamrani",
  email: "s.lamrani@bcskills.ma",
  motDePasse: "Demo@1234",
};

// --------------------------------------------------------------------------
// Utilitaires de mise en scène
// --------------------------------------------------------------------------

const pause = (ms) => new Promise((r) => setTimeout(r, ms));

/** Bandeau de légende : il donne à la vidéo sa ligne narrative. */
async function legende(page, titre, detail = "") {
  await page.evaluate(
    ([t, d]) => {
      let socle = document.getElementById("demo-legende");
      if (!socle) {
        socle = document.createElement("div");
        socle.id = "demo-legende";
        socle.style.cssText = [
          "position:fixed", "left:0", "right:0", "bottom:0", "z-index:2147483647",
          "padding:18px 28px", "pointer-events:none",
          "font-family:Inter,system-ui,sans-serif",
          "background:linear-gradient(to top,rgba(8,12,20,.94),rgba(8,12,20,0))",
          "color:#fff", "transition:opacity .25s",
        ].join(";");
        document.body.appendChild(socle);
      }
      socle.innerHTML =
        `<div style="font-size:19px;font-weight:650;letter-spacing:-.01em">${t}</div>` +
        (d ? `<div style="font-size:14px;opacity:.72;margin-top:3px">${d}</div>` : "");
      socle.style.opacity = "1";
    },
    [titre, detail]
  );
}

async function masquerLegende(page) {
  await page
    .evaluate(() => {
      const s = document.getElementById("demo-legende");
      if (s) s.style.opacity = "0";
    })
    .catch(() => {});
}

/** Carton plein écran : ouverture, transitions, conclusion. */
async function carton(page, titre, sousTitre, duree = 3200) {
  await page.evaluate(
    ([t, s]) => {
      const d = document.createElement("div");
      d.id = "demo-carton";
      d.style.cssText = [
        "position:fixed", "inset:0", "z-index:2147483647",
        "display:flex", "flex-direction:column",
        "align-items:center", "justify-content:center", "gap:14px",
        "background:#0b1220", "color:#fff",
        "font-family:Inter,system-ui,sans-serif", "text-align:center",
        "opacity:0", "transition:opacity .45s",
      ].join(";");
      d.innerHTML =
        `<div style="font-size:38px;font-weight:700;letter-spacing:-.02em;max-width:900px">${t}</div>` +
        `<div style="font-size:17px;opacity:.66;max-width:760px;line-height:1.5">${s}</div>`;
      document.body.appendChild(d);
      requestAnimationFrame(() => (d.style.opacity = "1"));
    },
    [titre, sousTitre]
  );
  await pause(duree);
  await page.evaluate(() => {
    const d = document.getElementById("demo-carton");
    if (!d) return;
    d.style.opacity = "0";
    setTimeout(() => d.remove(), 500);
  });
  await pause(600);
}

/** Saisie au rythme d'une frappe humaine : un remplissage instantané se lit mal. */
async function saisir(champ, texte) {
  await champ.click();
  await champ.pressSequentially(texte, { delay: 45 });
  await pause(180);
}

/** Descente douce : un saut de défilement empêche de suivre ce qui passe. */
async function defiler(page, cible, pixels, pas = 26) {
  for (let fait = 0; fait < pixels; fait += pas) {
    await cible.evaluate((el, p) => {
      if (el === document.scrollingElement) window.scrollBy(0, p);
      else el.scrollTop += p;
    }, pas);
    await pause(16);
  }
}

// --------------------------------------------------------------------------
// Étapes du scénario
// --------------------------------------------------------------------------

async function creerLeCompteCandidat(page) {
  await legende(page, "1 — Le candidat crée son compte",
    "Sahri Zaid, étudiant ingénieur, n'a encore jamais utilisé la plateforme.");
  await page.goto(`${BASE}/inscription`, { waitUntil: "networkidle" });
  await pause(1200);

  await page.getByRole("radio", { name: /Candidat/i }).click();
  await pause(400);

  await saisir(page.locator("#nom"), CANDIDAT.nom);
  await saisir(page.locator("#email"), CANDIDAT.email);
  await saisir(page.locator("#mdp"), CANDIDAT.motDePasse);
  await saisir(page.locator("#conf"), CANDIDAT.motDePasse);

  await legende(page, "1 — Le candidat crée son compte",
    "Le consentement au traitement automatisé du CV est demandé explicitement.");
  await page.locator('input[type="checkbox"]').first().check();
  await pause(1400);

  await page.getByRole("button", { name: /Créer mon compte|S'inscrire|Créer/i }).click();

  // Le compte peut déjà exister si la démonstration a déjà été jouée : on
  // poursuit alors par la connexion, sans faire échouer l'enregistrement.
  await Promise.race([
    page.waitForURL("**/connexion", { timeout: 15000 }).catch(() => null),
    page.waitForTimeout(6000),
  ]);
  await pause(800);
}

async function seConnecter(page, compte, numero, titre, detail) {
  await legende(page, `${numero} — ${titre}`, detail);
  if (!page.url().includes("/connexion")) {
    await page.goto(`${BASE}/connexion`, { waitUntil: "networkidle" });
  }
  await pause(900);

  const email = page.locator('input[type="email"]').first();
  const mdp = page.locator('input[type="password"]').first();
  await email.fill("");
  await saisir(email, compte.email);
  await mdp.fill("");
  await saisir(mdp, compte.motDePasse);
  await pause(400);

  await page.getByRole("button", { name: /Se connecter|Connexion/i }).click();
  await page.waitForURL((u) => !u.pathname.includes("/connexion"), { timeout: 25000 });
  await page.waitForLoadState("networkidle").catch(() => {});
  await pause(1600);
}

async function deposerLeCV(page) {
  await legende(page, "3 — Il ouvre l'offre qui l'intéresse",
    `« ${OFFRE} » — BC Skills, Rabat.`);
  await page.goto(`${BASE}/offres`, { waitUntil: "networkidle" });
  await pause(1600);

  const carte = page.getByRole("heading", { name: OFFRE }).first();
  await carte.scrollIntoViewIfNeeded();
  await pause(900);
  await carte.click();
  await page.waitForLoadState("networkidle").catch(() => {});
  await pause(1800);

  await legende(page, "3 — Il ouvre l'offre qui l'intéresse",
    "L'offre annonce ses critères avant tout dépôt : rien n'est évalué en secret.");
  await defiler(page, page.locator("html"), 420);
  await pause(2200);

  await legende(page, "4 — Il dépose son CV",
    "Un seul geste : le document est analysé immédiatement, à la seconde du dépôt.");
  await page.setInputFiles('input[type="file"]', CHEMIN_CV);
  await pause(1800);

  await page.getByRole("button", { name: /Envoyer ma candidature/i }).click();

  await legende(page, "4 — Il dépose son CV",
    "Extraction du texte, reconstitution du profil, comparaison à l'offre, note.");
  // L'analyse est synchrone : extraction, analyse linguistique, plongements,
  // modèle appris. Quelques secondes sur un poste ordinaire.
  await page
    .getByText(/candidature.*(envoyée|enregistrée|reçue)|Suivre ma candidature/i)
    .first()
    .waitFor({ timeout: 90000 })
    .catch(() => {});
  await pause(2600);
}

async function suivreSaCandidature(page) {
  await legende(page, "5 — Ce que le candidat voit de son côté",
    "Il suit l'avancement de sa candidature — il ne voit pas la note du recruteur.");
  await page.goto(`${BASE}/mes-candidatures`, { waitUntil: "networkidle" });
  await pause(3200);
}

async function seDeconnecter(page) {
  await page.getByRole("button", { name: /Menu utilisateur/i }).click();
  await pause(700);
  await page.getByRole("button", { name: /Se déconnecter/i }).click();
  await page.waitForURL("**/connexion", { timeout: 15000 }).catch(() => {});
  await pause(1000);
}

async function consulterCoteRecruteur(page) {
  await legende(page, "7 — La candidature apparaît dans son tableau",
    "Classée par note, aux côtés des autres candidatures de la même offre.");
  await page.goto(`${BASE}/candidatures`, { waitUntil: "networkidle" });
  await pause(2400);

  const recherche = page.getByPlaceholder(/Nom ou adresse/i).first();
  await saisir(recherche, "Sahri");
  await pause(2000);

  await legende(page, "8 — Le détail de la note",
    "Chaque point est rattaché à une composante — la note ne tombe pas du ciel.");
  await page.getByRole("button", { name: /Détails/i }).first().click();
  await pause(2600);

  // Le panneau latéral : note, critères, décomposition, profil reconstitué,
  // puis le CV lui-même. C'est la confrontation des deux qui fait la preuve.
  const panneau = page
    .locator("aside, [class*='overflow-y-auto']")
    .filter({ hasText: /Détail du calcul|Profil extrait/i })
    .first();
  const cible = (await panneau.count()) ? panneau : page.locator("html");

  await defiler(cible, cible, 300);
  await legende(page, "8 — Le détail de la note",
    "Compétences obligatoires, compétences souhaitées, proximité sémantique, expérience, diplôme.");
  await pause(3400);

  await defiler(cible, cible, 340);
  await legende(page, "9 — Le profil reconstitué à partir du CV",
    "Ce que la plateforme a lu — et, rubrique par rubrique, ce qu'elle n'a pas trouvé.");
  await pause(3600);

  await defiler(cible, cible, 380);
  await legende(page, "10 — Le CV, affiché à côté du profil",
    "Le recruteur vérifie lui-même : rien ne lui est demandé sur parole.");
  await pause(4200);

  await defiler(cible, cible, 360);
  await pause(3000);
}

// --------------------------------------------------------------------------
// Déroulé
// --------------------------------------------------------------------------

(async () => {
  if (!fs.existsSync(CHEMIN_CV)) {
    console.error(`CV introuvable : ${CHEMIN_CV}`);
    process.exit(1);
  }
  fs.mkdirSync(SORTIE, { recursive: true });

  const navigateur = await chromium.launch({
    headless: !VISIBLE,
    slowMo: 90,
    args: [`--window-size=${LARGEUR},${HAUTEUR + 120}`],
  });

  const contexte = await navigateur.newContext({
    viewport: { width: LARGEUR, height: HAUTEUR },
    recordVideo: { dir: SORTIE, size: { width: LARGEUR, height: HAUTEUR } },
    locale: "fr-FR",
    timezoneId: "Africa/Casablanca",
  });

  // La visite guidée s'ouvre d'elle-même à la première connexion d'un compte.
  // Elle est utile à un nouvel utilisateur et nuisible à une démonstration :
  // son voile assombrit l'écran et masque ce que la vidéo doit montrer. On la
  // déclare vue, sans toucher au code de l'application.
  await contexte.addInitScript(() => {
    const lire = Storage.prototype.getItem;
    Storage.prototype.getItem = function (cle) {
      if (typeof cle === "string" && cle.startsWith("skillseek:visite:")) {
        return "demo";
      }
      return lire.call(this, cle);
    };
  });

  const page = await contexte.newPage();
  page.setDefaultTimeout(30000);

  try {
    await page.goto(`${BASE}/connexion`, { waitUntil: "networkidle" });

    await carton(page, "SkillSeek AI",
      "Du dépôt d'un CV à la décision du recruteur — le parcours complet, sans coupure.", 4000);

    await creerLeCompteCandidat(page);
    await seConnecter(page, CANDIDAT, "2", "Il se connecte",
      "Le compte candidat est actif immédiatement.");
    await deposerLeCV(page);
    await suivreSaCandidature(page);

    await carton(page, "Côté recruteur",
      "La même candidature, vue par la personne qui doit décider.", 3400);

    await legende(page, "6 — Le recruteur qui porte l'offre se connecte",
      `${RECRUTEUR.nom} — BC Skills.`);
    await seDeconnecter(page);
    await seConnecter(page, RECRUTEUR, "6", "Le recruteur se connecte",
      `${RECRUTEUR.nom} — BC Skills, qui a publié l'offre.`);

    await consulterCoteRecruteur(page);

    await masquerLegende(page);
    await carton(page, "Le système propose, l'humain tranche.",
      "La plateforme classe, explique et signale. Elle ne décide pas : "
      + "chaque point de la note renvoie à une ligne du document, que le "
      + "recruteur peut aller vérifier lui-même.", 5200);
  } catch (erreur) {
    console.error("\nÉchec pendant l'enregistrement :", erreur.message);
    await page.screenshot({ path: path.join(SORTIE, "echec.png"), fullPage: true }).catch(() => {});
    console.error(`Capture de l'écran au moment de l'échec : ${path.join(SORTIE, "echec.png")}`);
  } finally {
    const video = page.video();
    await contexte.close();
    await navigateur.close();
    if (video) {
      const source = await video.path();
      const destination = path.join(SORTIE, "skillseek-demonstration.webm");
      fs.renameSync(source, destination);
      console.log(`\nVidéo enregistrée : ${destination}`);
      console.log("Conversion en MP4 si nécessaire :");
      console.log(`  ffmpeg -i "${destination}" -c:v libx264 -crf 20 -pix_fmt yuv420p skillseek-demonstration.mp4`);
    }
  }
})();
