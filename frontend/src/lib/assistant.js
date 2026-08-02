/**
 * Moteur de réponses de l'assistant RH — version Sprint 2.
 *
 * Les réponses sont CALCULÉES sur les données réelles chargées depuis l'API,
 * pas piochées dans une liste figée. Le remplacement par un LLM (LangChain/RAG)
 * au Sprint 4 conservera cette interface : repondre(question, donnees).
 */
import { SEUIL_RETENU, PLAFOND_TOP } from "./scoring";

const STATUT_LIBELLE = {
  received: "Reçue", under_review: "En étude", shortlisted: "Présélectionné",
  interview: "Entretien", hired: "Recruté", rejected: "Non retenu",
};

/** Extrait un nombre d'années mentionné dans la question ("plus de 5 ans"). */
function extraireAnnees(q) {
  const m = q.match(/(\d+)\s*an/);
  return m ? Number(m[1]) : null;
}

/** Retrouve une offre citée dans la question par correspondance de mots. */
function trouverOffre(q, offres) {
  const mots = q.split(/\s+/).filter((m) => m.length > 3);
  let meilleure = null;
  let meilleurScore = 0;
  for (const o of offres) {
    const titre = o.title.toLowerCase();
    const score = mots.filter((m) => titre.includes(m)).length;
    if (score > meilleurScore) { meilleurScore = score; meilleure = o; }
  }
  return meilleurScore > 0 ? meilleure : null;
}

const moyenne = (nombres) =>
  nombres.length ? Math.round(nombres.reduce((a, b) => a + b, 0) / nombres.length) : null;

/**
 * @param {string} question
 * @param {{offres: array, candidatures: array}} donnees
 * @returns {{texte: string, tableau?: {colonnes: string[], lignes: array[]}, lien?: {href: string, libelle: string}}}
 */
export function repondre(question, donnees) {
  const q = question.toLowerCase().trim();
  const { offres = [], candidatures = [] } = donnees;

  if (!candidatures.length && !offres.length) {
    return { texte: "Je n'ai encore aucune donnée à analyser. Publiez une offre et recevez des candidatures pour que je puisse vous répondre." };
  }

  const offreCitee = trouverOffre(q, offres);
  const scopeCandidatures = offreCitee
    ? candidatures.filter((c) => c.offer?.id === offreCitee.id)
    : candidatures;

  // ---- Entonnoir / conversion ----
  if (/funnel|entonnoir|conversion|pipeline/.test(q)) {
    const recues = scopeCandidatures.length;
    const preselec = scopeCandidatures.filter((c) => (c.score ?? 0) >= SEUIL_RETENU).length;
    const entretiens = scopeCandidatures.filter((c) => c.status === "interview").length;
    const recrutes = scopeCandidatures.filter((c) => c.status === "hired").length;
    const taux = (a, b) => (b ? `${Math.round((a / b) * 100)}%` : "—");

    return {
      texte: `Voici l'entonnoir${offreCitee ? ` pour « ${offreCitee.title} »` : " toutes offres confondues"} : ${recues} candidature(s) reçue(s), ${preselec} au-dessus du seuil de ${SEUIL_RETENU}, ${entretiens} en entretien et ${recrutes} recrutement(s).`,
      tableau: {
        colonnes: ["Étape", "Volume", "Conversion"],
        lignes: [
          ["Candidatures reçues", recues, "100%"],
          ["Filtre IA", preselec, taux(preselec, recues)],
          ["Entretiens", entretiens, taux(entretiens, preselec)],
          ["Recrutements", recrutes, taux(recrutes, entretiens)],
        ],
      },
      lien: { href: "/dashboard", libelle: "Ouvrir le tableau de bord" },
    };
  }

  // ---- Score moyen ----
  if (/score\s*moyen|moyenne/.test(q)) {
    const scores = scopeCandidatures.map((c) => c.score).filter((s) => s != null);
    const m = moyenne(scores);
    if (m == null) return { texte: "Aucun score n'a encore été calculé sur ce périmètre." };
    return {
      texte: offreCitee
        ? `Le score moyen sur « ${offreCitee.title} » est de ${m}/100, calculé sur ${scores.length} candidature(s).`
        : `Le score moyen toutes offres confondues est de ${m}/100, sur ${scores.length} candidature(s) évaluée(s).`,
    };
  }

  // ---- Meilleurs profils ----
  if (/meilleur|top|classement|shortlist|préséle|presele/.test(q)) {
    const tries = [...scopeCandidatures]
      .filter((c) => (c.score ?? 0) >= SEUIL_RETENU)
      .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
      .slice(0, PLAFOND_TOP);

    if (!tries.length) return { texte: `Aucune candidature n'atteint le seuil de ${SEUIL_RETENU}/100 sur ce périmètre.` };

    return {
      texte: `Voici les ${tries.length} meilleur(s) profil(s)${offreCitee ? ` sur « ${offreCitee.title} »` : ""} :`,
      tableau: {
        colonnes: ["Candidat", "Offre", "Score", "Statut"],
        lignes: tries.map((c) => [
          c.candidate?.full_name || "—",
          c.offer?.title || "—",
          `${c.score}/100`,
          STATUT_LIBELLE[c.status] || c.status,
        ]),
      },
      lien: { href: "/candidatures", libelle: "Voir toutes les candidatures" },
    };
  }

  // ---- Comptage par expérience ----
  const annees = extraireAnnees(q);
  if (annees != null && /expérience|experience/.test(q)) {
    const concernes = scopeCandidatures.filter((c) => {
      const details = c.score_details || {};
      return !(details.eliminatoires || []).some((m) => m.includes("Expérience"));
    });
    return {
      texte: `Sur ce périmètre, ${concernes.length} candidature(s) sur ${scopeCandidatures.length} remplissent le critère d'expérience requis. L'extraction détaillée des années d'expérience depuis les CV sera disponible avec le module d'analyse (Sprint 3).`,
    };
  }

  // ---- Écartées ----
  if (/écart|ecart|rejet|refus|sous le seuil/.test(q)) {
    const ecartees = scopeCandidatures.filter((c) => (c.score ?? 0) < SEUIL_RETENU);
    const motifs = {};
    ecartees.forEach((c) => {
      (c.score_details?.eliminatoires || []).forEach((m) => {
        const cle = m.split(" ")[0];
        motifs[cle] = (motifs[cle] || 0) + 1;
      });
    });
    const detail = Object.entries(motifs).map(([k, v]) => `${v} pour un motif « ${k} »`).join(", ");
    return {
      texte: `${ecartees.length} candidature(s) sont sous le seuil de ${SEUIL_RETENU}/100${detail ? ` : ${detail}` : ""}. Elles restent consultables et vous pouvez les repêcher à tout moment.`,
      lien: { href: "/candidatures", libelle: "Consulter les candidatures écartées" },
    };
  }

  // ---- En attente d'action ----
  if (/attente|à traiter|a traiter|action|faire/.test(q)) {
    const attente = scopeCandidatures.filter((c) => ["received", "under_review"].includes(c.status));
    if (!attente.length) return { texte: "Aucune candidature n'attend d'action de votre part. Tout est à jour." };
    return {
      texte: `${attente.length} candidature(s) attendent une décision de votre part.`,
      tableau: {
        colonnes: ["Candidat", "Offre", "Score"],
        lignes: attente.slice(0, 10).map((c) => [
          c.candidate?.full_name || "—",
          c.offer?.title || "—",
          c.score != null ? `${c.score}/100` : "—",
        ]),
      },
      lien: { href: "/candidatures", libelle: "Traiter les candidatures" },
    };
  }

  // ---- Comparaison entre offres ----
  if (/compar|versus|entre les offres|par offre/.test(q)) {
    if (!offres.length) return { texte: "Aucune offre à comparer pour le moment." };
    return {
      texte: "Comparaison de vos offres :",
      tableau: {
        colonnes: ["Offre", "Candidatures", "Score moyen", "Entretiens"],
        lignes: offres.map((o) => {
          const liste = candidatures.filter((c) => c.offer?.id === o.id);
          const scores = liste.map((c) => c.score).filter((s) => s != null);
          const m = moyenne(scores);
          return [
            o.title,
            liste.length,
            m != null ? `${m}/100` : "—",
            liste.filter((c) => c.status === "interview").length,
          ];
        }),
      },
    };
  }

  // ---- Nombre de candidatures / offres ----
  if (/combien/.test(q)) {
    if (/offre/.test(q)) {
      const ouvertes = offres.filter((o) => o.status === "open").length;
      return { texte: `Vous avez ${offres.length} offre(s) au total, dont ${ouvertes} actuellement ouverte(s).` };
    }
    return {
      texte: offreCitee
        ? `« ${offreCitee.title} » a reçu ${scopeCandidatures.length} candidature(s).`
        : `Vous avez reçu ${candidatures.length} candidature(s) au total, réparties sur ${offres.length} offre(s).`,
    };
  }

  // ---- Hors périmètre : réponse honnête + suggestions ----
  return {
    texte:
      "Je n'ai pas su interpréter cette question. Je peux analyser vos données de recrutement : volumes de candidatures, scores moyens, meilleurs profils, entonnoir de conversion, candidatures écartées et leurs motifs, ou comparaison entre vos offres.",
  };
}

export const SUGGESTIONS = [
  "Quels sont les meilleurs profils actuellement ?",
  "Montre-moi l'entonnoir de ce mois",
  "Quel est le score moyen par offre ?",
  "Quelles candidatures attendent une décision ?",
  "Combien de candidatures ont été écartées et pourquoi ?",
];
