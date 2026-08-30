/** Règles de l'interface, isolées de tout rendu.
 *
 * Ces fonctions étaient écrites à l'intérieur des composants. Elles en sont
 * sorties pour une raison précise : une règle enfouie dans un composant ne se
 * teste qu'en montant tout l'écran, ce qui coûte cher et casse au moindre
 * changement de présentation. Isolée, elle se vérifie en une ligne.
 *
 * Aucune de ces fonctions ne connaît React.
 */

/** Deux listes de codes désignent-elles le même ensemble de droits ?
 *
 * Comparer des tableaux triés puis sérialisés donnerait le bon résultat, mais
 * dirait mal l'intention : ce qui compte n'est pas un ordre, c'est une égalité
 * d'ensembles. La comparaison des tailles précède la vérification d'inclusion
 * pour rester juste même si un code apparaissait deux fois.
 */
export function memesDroits(a, b) {
  const gauche = new Set(a || []);
  const droite = new Set(b || []);
  return gauche.size === droite.size && [...gauche].every((c) => droite.has(c));
}

/** Comparateur pour l'alphabet français.
 *
 * Le tri par défaut de JavaScript compare les caractères Unicode bruts et
 * range « électricité » après « zsh ». Sur une liste lue par un recruteur,
 * l'ordre attendu est celui du dictionnaire.
 */
export function comparerFr(a, b) {
  return String(a).localeCompare(String(b), "fr");
}

/** Trie une liste de libellés selon l'alphabet français, sans muter l'entrée. */
export function trierFr(valeurs) {
  return [...(valeurs || [])].sort(comparerFr);
}

/** Compétences distinctes présentes dans un lot de candidatures.
 *
 * Ne proposer comme filtre que ce qui donnera un résultat : un filtre qui
 * renvoie toujours une liste vide est pire qu'un filtre absent.
 */
export function competencesDisponibles(candidatures) {
  const toutes = new Set();
  (candidatures || []).forEach((c) => {
    (c?.score_details?.profil_ats?.skills || []).forEach((s) => toutes.add(s));
  });
  return trierFr([...toutes]);
}

/** Y a-t-il un filtre actif ?
 *
 * Rendue explicitement booléenne : en JSX, `{valeur && <Bandeau/>}` affiche la
 * valeur elle-même lorsqu'elle vaut 0, ce qui fait apparaître un « 0 » nu dans
 * la page.
 */
export function filtreActif(...valeurs) {
  return valeurs.some((v) => Boolean(v));
}

/** Classe une candidature selon la règle de présélection RG-01.
 *
 * Rend « ecartee », « preselectionnee » ou « retenue ». La règle est ici
 * dupliquée depuis le service applicatif, qui reste seul juge : l'interface
 * s'en sert uniquement pour afficher le bon libellé sans attendre un aller
 * et retour avec le serveur.
 */
export const SEUIL_PRESELECTION = 50;
export const PLAFOND_PRESELECTION = 10;

export function classer(score, rang) {
  if (score === null || score === undefined) return "en_attente";
  if (score < SEUIL_PRESELECTION) return "ecartee";
  if (rang !== undefined && rang < PLAFOND_PRESELECTION) return "preselectionnee";
  return "retenue";
}
