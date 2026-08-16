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
};
