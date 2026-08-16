import { Html, Head, Main, NextScript } from "next/document";

/**
 * Le thème est appliqué avant le premier rendu par un script synchrone.
 * Sans lui, la page s'afficherait brièvement dans le thème par défaut avant
 * de basculer, produisant un clignotement désagréable à chaque chargement.
 */
const APPLIQUER_THEME = `
(function () {
  try {
    var choix = localStorage.getItem('skillseek_theme');
    if (!choix) {
      choix = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }
    document.documentElement.setAttribute('data-theme', choix);
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();
`;

export default function Document() {
  return (
    <Html lang="fr" data-theme="dark">
      <Head>
        <script dangerouslySetInnerHTML={{ __html: APPLIQUER_THEME }} />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
