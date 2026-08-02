/**
 * Moteur de score côté client — miroir de la logique serveur (Sprint 3).
 * Sert à l'affichage explicable : le calcul réel fait foi côté API.
 * Règle RG-01 du cahier des charges.
 */

export const SEUIL_RETENU = 50;
export const PLAFOND_TOP = 10;

/** Compare un candidat à une offre et produit un score /100 + son explication. */
export function calculerScore(candidat, offre) {
  const requises = (offre.required_skills || []).map((s) => s.toLowerCase());
  const possedees = (candidat.skills || []).map((s) => s.toLowerCase());

  const trouvees = requises.filter((s) => possedees.includes(s));
  const manquantes = requises.filter((s) => !possedees.includes(s));

  // 1. Critères éliminatoires (système expert) — priment sur tout le reste.
  const eliminatoires = [];
  if (offre.min_experience_years && candidat.experience_years < offre.min_experience_years) {
    eliminatoires.push(
      `Expérience ${candidat.experience_years} an(s) < ${offre.min_experience_years} an(s) requis`
    );
  }
  if (offre.min_degree && !diplomeSuffisant(candidat.degree, offre.min_degree)) {
    eliminatoires.push(`Diplôme ${candidat.degree || "non renseigné"} < ${offre.min_degree} requis`);
  }

  // 2. Composantes du score
  const partCompetences = requises.length ? (trouvees.length / requises.length) * 70 : 70;
  const ratioExp = offre.min_experience_years
    ? Math.min(candidat.experience_years / offre.min_experience_years, 1.5) / 1.5
    : 1;
  const partExperience = ratioExp * 20;
  const partDiplome = diplomeSuffisant(candidat.degree, offre.min_degree) ? 10 : 0;

  let score = Math.round(partCompetences + partExperience + partDiplome);
  if (eliminatoires.length) score = Math.min(score, 45); // écarté par règle

  return {
    score: Math.max(0, Math.min(100, score)),
    competencesTrouvees: trouvees,
    competencesManquantes: manquantes,
    eliminatoires,
    detail: [
      { libelle: "Correspondance des compétences", valeur: Math.round(partCompetences), max: 70 },
      { libelle: "Années d'expérience", valeur: Math.round(partExperience), max: 20 },
      { libelle: "Niveau de diplôme", valeur: partDiplome, max: 10 },
    ],
  };
}

const NIVEAUX = { "bac": 0, "bac+2": 2, "bac+3": 3, "bac+5": 5, "doctorat": 8 };

function diplomeSuffisant(candidat, requis) {
  if (!requis) return true;
  const a = NIVEAUX[(candidat || "").toLowerCase()] ?? -1;
  const b = NIVEAUX[requis.toLowerCase()] ?? 0;
  return a >= b;
}

/** Applique la règle RG-01 : seuil à 50, puis plafond des 10 meilleurs. */
export function appliquerRegleTop(candidatures) {
  const retenues = candidatures.filter((c) => (c.score ?? 0) >= SEUIL_RETENU);
  const triees = [...retenues].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  return {
    top: triees.slice(0, PLAFOND_TOP),
    ecartees: candidatures.filter((c) => (c.score ?? 0) < SEUIL_RETENU),
    toutes: [...candidatures].sort((a, b) => (b.score ?? 0) - (a.score ?? 0)),
  };
}

/** Couleur du badge selon le score (vert ≥70, orange 50-69, gris <50). */
export function couleurScore(score) {
  if (score == null) return { texte: "text-txt2", fond: "bg-bordure/40", anneau: "#8B98B8" };
  if (score >= 70) return { texte: "text-succes", fond: "bg-succes/10", anneau: "#34D399" };
  if (score >= SEUIL_RETENU) return { texte: "text-alerte", fond: "bg-alerte/10", anneau: "#F59E0B" };
  return { texte: "text-txt2", fond: "bg-bordure/40", anneau: "#8B98B8" };
}
