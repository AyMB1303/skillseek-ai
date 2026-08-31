const developpement = process.env.NODE_ENV !== "production";

// Origine de l'API, deduite de l'adresse configuree. En production
// l'interface et l'API sont servies par le meme proxy, donc la meme origine ;
// sur un poste de developpement elles vivent sur deux ports differents, et il
// faut nommer le second sous peine de voir le navigateur refuser chaque appel.
const origineApi = (() => {
  try {
    return new URL(
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api"
    ).origin;
  } catch {
    return "";
  }
})();

// Politique de securite du contenu.
//
// Elle enumere ce que la page a le droit de charger et de joindre. Son
// interet est de limiter les degats d'une injection : meme si du script
// etranger parvenait dans la page, le navigateur refuserait de l'executer
// s'il ne vient pas d'une source declaree.
//
// `unsafe-inline` reste necessaire : Next depose dans la page les donnees
// d'hydratation et quelques styles sous forme de balises en ligne. Une
// politique plus stricte demanderait un jeton unique par requete, ce que le
// routeur employe ici ne fournit pas. La politique est donc reelle mais
// large, et je prefere l'ecrire ainsi plutot que d'annoncer une protection
// que l'application ne respecte pas.
const politiqueContenu = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${developpement ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  `connect-src 'self' ${origineApi}${developpement ? " ws: wss:" : ""}`.trim(),
  // Aucune ressource externe n'est incorporee, et la plateforme ne doit
  // jamais s'afficher dans le cadre d'un autre site.
  "frame-src 'none'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  // Empeche la reecriture de l'adresse de base, qui detournerait tous les
  // liens relatifs de la page.
  "base-uri 'self'",
  // Un formulaire ne peut envoyer ses donnees qu'a la plateforme elle-meme.
  "form-action 'self'",
].join("; ");

/** @type {import('next').NextConfig} */
module.exports = {
  reactStrictMode: true,

  // Sortie autonome : Next assemble dans `.next/standalone` le serveur et les
  // seules dependances reellement atteintes par le code. L'image de production
  // n'embarque donc pas `node_modules` en entier — quelques dizaines de Mo au
  // lieu de plusieurs centaines.
  output: "standalone",

  env: {
    // Lue a la construction : une variable `NEXT_PUBLIC_*` est inscrite dans le
    // bundle envoye au navigateur, elle ne peut pas etre changee au demarrage
    // du conteneur. D'ou l'argument de construction dans le Dockerfile.
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api",
  },

  // Next annonce sa presence par un en-tete `X-Powered-By`. Renseigner un
  // attaquant sur la technologie et sa version lui evite d'avoir a la
  // deviner ; l'information ne sert a personne d'autre.
  poweredByHeader: false,

  // En-tetes de securite.
  //
  // Ils ne corrigent aucun defaut du code : ils indiquent au navigateur des
  // restrictions qu'il applique lui-meme. C'est une couche que l'analyse
  // statique ne peut pas reclamer, puisqu'elle n'existe qu'a l'execution —
  // c'est l'analyse dynamique de la chaine qui les a signales absents.
  //
  // Poses ici plutot que dans la configuration du proxy : ils suivent alors
  // l'application partout, y compris sur un poste de developpement et dans
  // les manifestes Kubernetes, au lieu de dependre de ce qui se trouve
  // devant elle.
  async headers() {
    return [
      {
        source: "/:chemin*",
        headers: [
          // Interdit l'affichage de la plateforme dans un cadre. Sans cela,
          // un site tiers peut la superposer de maniere invisible et
          // recuperer les clics d'un recruteur authentifie.
          { key: "X-Frame-Options", value: "DENY" },
          // Empeche le navigateur de deviner un type de contenu. Un fichier
          // deposé et servi ensuite comme du texte ne doit pas pouvoir etre
          // reinterprete comme du script.
          { key: "X-Content-Type-Options", value: "nosniff" },
          // L'adresse d'une page interne — qui contient un identifiant de
          // candidature — ne doit pas partir dans l'en-tete `Referer` vers
          // un site externe.
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // Aucune interface de la plateforme n'a besoin de la camera, du
          // micro ni de la position. On le declare plutot que de laisser la
          // porte ouverte.
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
          },
          // Isole le contexte de navigation : une fenetre ouverte depuis la
          // plateforme ne garde pas de prise sur celle qui l'a ouverte.
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
          { key: "Content-Security-Policy", value: politiqueContenu },
        ],
      },
    ];
  },
};
