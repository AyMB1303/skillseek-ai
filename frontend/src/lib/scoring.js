/**
 * Présentation du score — aucun calcul.
 *
 * Ce fichier contenait jusqu'ici un second moteur de score, écrit au sprint 3
 * quand l'interface fonctionnait encore sur des données simulées. Il en
 * restait une copie figée des anciennes pondérations (70 / 20 / 10, plafond
 * plat à 45), alors que le moteur serveur en est à `ats-4.0` : compétences
 * obligatoires 35, souhaitées 10, similarité sémantique 25, expérience 20,
 * diplôme 10, avec réserves graduées et ajustement du modèle borné.
 *
 * Aucun écran ne l'appelait plus — le score affiché a toujours été celui de
 * l'API. Mais un calcul mort qui produit un nombre plausible finit par être
 * rebranché par mégarde, et il devient alors impossible de dire lequel des
 * deux fait foi. Il est donc supprimé plutôt que corrigé.
 *
 * **Le score est calculé une seule fois, côté serveur, et transporté tel quel
 * jusqu'à l'écran.** Ne rétablissez pas de calcul ici : ce qui manquerait à
 * l'affichage doit être ajouté à `score_details` dans la réponse de l'API.
 *
 * Ne subsistent que des constantes de lecture et le choix des couleurs.
 */

/** Seuil de présélection (RG-01), repris du serveur pour les libellés. */
export const SEUIL_RETENU = 50;

/** Taille maximale de la liste restreinte (RG-01). */
export const PLAFOND_TOP = 10;

/** Couleur du badge selon le score (vert ≥70, orange 50-69, gris <50).
 *
 *  `anneau` renvoie une couleur CSS calculée à partir des variables de thème,
 *  afin que la jauge reste lisible en mode clair comme en mode sombre.
 */
export function couleurScore(score) {
  const gris = {
    texte: "text-txt2",
    fond: "bg-bordure/40",
    anneau: "rgb(var(--c-txt2))",
  };
  if (score == null) return gris;
  if (score >= 70) {
    return { texte: "text-succes", fond: "bg-succes/10", anneau: "rgb(var(--c-succes))" };
  }
  if (score >= SEUIL_RETENU) {
    return { texte: "text-alerte", fond: "bg-alerte/10", anneau: "rgb(var(--c-alerte))" };
  }
  return gris;
}
