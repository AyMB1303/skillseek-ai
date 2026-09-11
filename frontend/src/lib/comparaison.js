/** Mise en regard de plusieurs candidatures — aucun calcul.
 *
 * Ce module réorganise ce que le serveur a déjà produit. Il ne recalcule
 * aucune note, ne pondère rien et n'ordonne personne : la mise en garde de
 * « scoring.js » vaut ici mot pour mot. Ce qui manquerait à la comparaison
 * doit être ajouté à `score_details` côté serveur, pas reconstitué ici.
 *
 * Trois décisions de fond gouvernent ce fichier.
 *
 * **On ne compare qu'à l'intérieur d'une même offre.** Deux candidatures
 * déposées sur des postes différents n'ont ni les mêmes compétences exigées
 * ni les mêmes composantes : les mettre côte à côte produirait un tableau
 * lisible et faux. La restriction n'est pas une simplification, c'est la
 * condition pour que la comparaison veuille dire quelque chose.
 *
 * **La comparaison ne désigne pas de vainqueur.** Le classement existe déjà,
 * il est produit par le moteur et il est justifié ligne à ligne. Ce que la
 * liste triée ne montre pas, c'est *où* deux candidatures s'écartent — un
 * écart de quatre points peut venir d'une compétence bloquante absente ou
 * d'un demi-point sur chacune des cinq composantes, et ces deux situations
 * n'appellent pas la même décision.
 *
 * **Ce qui ne diffère pas est du bruit.** Une ligne identique chez tout le
 * monde n'apprend rien et éloigne les lignes qui comptent. Elle est donc
 * marquée comme telle, à charge pour l'écran de la replier.
 */

import { comparerFr, trierFr } from "./regles";

/** Nombre de candidatures qu'une comparaison accepte.
 *
 * Deux au minimum, sans quoi il n'y a rien à comparer. Trois au maximum :
 * au-delà, les colonnes deviennent trop étroites pour être lues sur un écran
 * ordinaire, et l'exercice redevient une liste — que l'écran principal fait
 * déjà mieux.
 */
export const MINIMUM_COMPARABLE = 2;
export const MAXIMUM_COMPARABLE = 3;

/** Deux candidatures portent-elles sur la même offre ? */
export function memeOffre(a, b) {
  return (a?.offer?.id ?? null) === (b?.offer?.id ?? null) && a?.offer?.id != null;
}

/** La sélection courante peut-elle être comparée, et sinon pourquoi ?
 *
 * Renvoyer le motif plutôt qu'un simple booléen permet à l'écran de dire au
 * recruteur ce qui manque, au lieu de désactiver un bouton sans explication.
 */
export function etatSelection(candidatures) {
  const liste = candidatures || [];
  if (liste.length < MINIMUM_COMPARABLE) {
    return {
      comparable: false,
      motif: `Sélectionnez au moins ${MINIMUM_COMPARABLE} candidatures.`,
    };
  }
  if (liste.length > MAXIMUM_COMPARABLE) {
    return {
      comparable: false,
      motif: `${MAXIMUM_COMPARABLE} candidatures au maximum.`,
    };
  }
  const [premiere, ...reste] = liste;
  if (!reste.every((c) => memeOffre(premiere, c))) {
    return {
      comparable: false,
      motif:
        "Les candidatures comparées doivent porter sur la même offre : " +
        "les compétences exigées, et donc les composantes de la note, " +
        "diffèrent d'un poste à l'autre.",
    };
  }
  if (liste.some((c) => c.score == null)) {
    return {
      comparable: false,
      motif: "Une des candidatures n'a pas encore été analysée.",
    };
  }
  return { comparable: true, motif: "" };
}

/** Composantes de la note, alignées entre candidatures.
 *
 * Le moteur omet une composante lorsqu'elle ne s'applique pas — pas de
 * compétences souhaitées déclarées sur l'offre, pas de similarité sémantique
 * calculée. Les listes reçues n'ont donc pas forcément la même longueur ni le
 * même ordre. On les aligne sur les libellés, et une composante absente vaut
 * `null` plutôt que zéro : « non applicable » et « zéro point » sont deux
 * informations différentes, et les confondre ferait passer un candidat pour
 * mauvais là où la question ne lui a pas été posée.
 */
export function lignesComposantes(candidatures) {
  const liste = candidatures || [];
  const ordre = [];
  const maxima = new Map();

  for (const candidature of liste) {
    for (const composante of candidature.score_details?.composantes || []) {
      if (!maxima.has(composante.libelle)) {
        ordre.push(composante.libelle);
        maxima.set(composante.libelle, composante.max);
      }
    }
  }

  return ordre.map((libelle) => {
    const valeurs = liste.map((candidature) => {
      const trouvee = (candidature.score_details?.composantes || []).find(
        (c) => c.libelle === libelle
      );
      return trouvee ? trouvee.valeur : null;
    });
    const presentes = valeurs.filter((v) => v != null);
    return {
      libelle,
      max: maxima.get(libelle),
      valeurs,
      // « Identique » se juge sur les valeurs réellement présentes : une
      // composante absente chez l'un ne rend pas la ligne discriminante.
      identique: new Set(presentes).size <= 1,
      meilleure: presentes.length ? Math.max(...presentes) : null,
    };
  });
}

/** Matrice des compétences exigées par l'offre.
 *
 * L'ensemble est l'union des compétences trouvées et manquantes relevées sur
 * chaque candidature : c'est exactement la liste des exigences de l'offre,
 * puisque le moteur classe chacune dans l'une ou l'autre. On ne la lit pas
 * dans l'offre elle-même — la candidature transporte déjà le verdict, et
 * aller le rechercher ailleurs introduirait une seconde source de vérité.
 */
export function matriceCompetences(candidatures, { souhaitees = false } = {}) {
  const liste = candidatures || [];
  const cle = souhaitees
    ? ["competences_souhaitees_trouvees", "competences_souhaitees_manquantes"]
    : ["competences_trouvees", "competences_manquantes"];

  const exigees = new Set();
  for (const candidature of liste) {
    for (const champ of cle) {
      for (const competence of candidature.score_details?.[champ] || []) {
        exigees.add(competence);
      }
    }
  }

  return trierFr([...exigees]).map((competence) => {
    const detentions = liste.map((candidature) =>
      (candidature.score_details?.[cle[0]] || []).includes(competence)
    );
    return {
      competence,
      detentions,
      identique: new Set(detentions).size <= 1,
      // Une compétence que personne ne détient dit quelque chose de l'offre,
      // pas des candidats : elle est signalée pour ne pas être lue comme un
      // reproche adressé à chacun.
      absenteChezTous: detentions.every((d) => d === false),
    };
  });
}

/** Motifs d'écartement, par candidature.
 *
 * Distincts des composantes : un critère éliminatoire ne retire pas des
 * points, il plafonne la note. Le rappeler dans la comparaison évite la
 * lecture fautive d'un écart de note comme une différence de degré, alors
 * qu'il s'agit d'une différence de nature.
 */
export function lignesEliminatoires(candidatures) {
  return (candidatures || []).map((candidature) => ({
    id: candidature.id,
    eliminatoires: candidature.score_details?.eliminatoires || [],
    reserves: candidature.score_details?.reserves || [],
  }));
}

/** Assemble la comparaison complète, prête à afficher. */
export function construireComparaison(candidatures) {
  const liste = [...(candidatures || [])].sort((a, b) => {
    // Ordre de lecture : la note décroissante, puis le nom pour départager.
    // Il reprend celui de la liste d'où vient la sélection ; en changer
    // obligerait le recruteur à retrouver ses repères.
    if ((b.score ?? -1) !== (a.score ?? -1)) return (b.score ?? -1) - (a.score ?? -1);
    return comparerFr(a.candidate?.full_name || "", b.candidate?.full_name || "");
  });

  const composantes = lignesComposantes(liste);
  const obligatoires = matriceCompetences(liste);
  const souhaitees = matriceCompetences(liste, { souhaitees: true });

  return {
    candidatures: liste,
    offre: liste[0]?.offer || null,
    composantes,
    obligatoires,
    souhaitees,
    eliminatoires: lignesEliminatoires(liste),
    // Compte des lignes qui séparent réellement les candidatures. C'est le
    // seul chiffre que cet écran produit, et il répond à la question posée :
    // « sur quoi diffèrent-ils ? ». Zéro est une réponse utile — elle dit
    // que la note ne les départage pas.
    nombreDifferences:
      composantes.filter((l) => !l.identique).length +
      obligatoires.filter((l) => !l.identique).length +
      souhaitees.filter((l) => !l.identique).length,
  };
}
