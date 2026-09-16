/** Tests de la mise en regard de candidatures.
 *
 * Les cas retenus sont ceux où une comparaison peut mentir sans le montrer :
 * une composante absente confondue avec un zéro, deux offres différentes
 * mises côte à côte, une ligne identique présentée comme un écart. Aucun ne
 * se verrait à l'écran — le tableau s'afficherait, bien aligné, et le
 * recruteur en tirerait une conclusion fausse.
 */
import { describe, it, expect } from "vitest";
import {
  MAXIMUM_COMPARABLE,
  construireComparaison,
  etatSelection,
  lignesComposantes,
  matriceCompetences,
  memeOffre,
} from "./comparaison";

/** Fabrique une candidature minimale, à la forme de l'API. */
function candidature({
  id = 1,
  nom = "Test",
  score = 80,
  offre = 7,
  composantes = [],
  trouvees = [],
  manquantes = [],
  souhaiteesTrouvees = [],
  souhaiteesManquantes = [],
  eliminatoires = [],
} = {}) {
  return {
    id,
    score,
    candidate: { id, full_name: nom, email: `${id}@test.local` },
    offer: offre == null ? null : { id: offre, title: `Offre ${offre}` },
    score_details: {
      composantes,
      competences_trouvees: trouvees,
      competences_manquantes: manquantes,
      competences_souhaitees_trouvees: souhaiteesTrouvees,
      competences_souhaitees_manquantes: souhaiteesManquantes,
      eliminatoires,
      reserves: [],
    },
  };
}

// --------------------------- Recevabilité --------------------------------

describe("etatSelection — ce qu'une comparaison accepte", () => {
  it("refuse une sélection d'une seule candidature", () => {
    expect(etatSelection([candidature()]).comparable).toBe(false);
  });

  it("refuse au-delà du maximum lisible", () => {
    const trop = Array.from({ length: MAXIMUM_COMPARABLE + 1 }, (_, i) =>
      candidature({ id: i + 1 })
    );
    expect(etatSelection(trop).comparable).toBe(false);
  });

  it("refuse deux candidatures portant sur des offres différentes", () => {
    /* C'est le refus qui compte le plus : le tableau se serait affiché
       normalement, en alignant des composantes qui ne mesurent pas la même
       chose. Une comparaison lisible et fausse est pire qu'un refus. */
    const etat = etatSelection([
      candidature({ id: 1, offre: 7 }),
      candidature({ id: 2, offre: 8 }),
    ]);
    expect(etat.comparable).toBe(false);
    expect(etat.motif).toMatch(/même offre/i);
  });

  it("refuse une candidature non analysée", () => {
    const etat = etatSelection([
      candidature({ id: 1 }),
      candidature({ id: 2, score: null }),
    ]);
    expect(etat.comparable).toBe(false);
  });

  it("accepte deux candidatures analysées sur la même offre", () => {
    expect(
      etatSelection([candidature({ id: 1 }), candidature({ id: 2 })]).comparable
    ).toBe(true);
  });
});

describe("memeOffre", () => {
  it("refuse deux candidatures sans offre plutôt que de les dire identiques", () => {
    /* Deux valeurs nulles sont égales au sens de JavaScript. Les traiter
       comme une même offre autoriserait une comparaison entre postes
       inconnus. */
    expect(memeOffre(candidature({ offre: null }), candidature({ offre: null })))
      .toBe(false);
  });
});

// --------------------------- Composantes ---------------------------------

describe("lignesComposantes — alignement des composantes", () => {
  const avecSemantique = candidature({
    id: 1,
    composantes: [
      { libelle: "Compétences obligatoires", valeur: 30, max: 35 },
      { libelle: "Proximité sémantique CV / offre", valeur: 19, max: 25 },
    ],
  });
  const sansSemantique = candidature({
    id: 2,
    composantes: [{ libelle: "Compétences obligatoires", valeur: 30, max: 35 }],
  });

  it("distingue une composante absente d'une composante à zéro", () => {
    /* Le moteur omet la similarité sémantique quand il ne l'a pas calculée.
       La porter à zéro ferait passer le candidat pour mauvais là où la
       question ne lui a pas été posée. */
    const lignes = lignesComposantes([avecSemantique, sansSemantique]);
    const semantique = lignes.find((l) => l.libelle.startsWith("Proximité"));
    expect(semantique.valeurs).toEqual([19, null]);
    expect(semantique.valeurs[1]).not.toBe(0);
  });

  it("ne compte pas comme un écart une composante absente chez l'un", () => {
    const lignes = lignesComposantes([avecSemantique, sansSemantique]);
    expect(lignes.find((l) => l.libelle.startsWith("Proximité")).identique).toBe(true);
  });

  it("repère une ligne où les valeurs diffèrent", () => {
    const lignes = lignesComposantes([
      candidature({ id: 1, composantes: [{ libelle: "Expérience", valeur: 20, max: 20 }] }),
      candidature({ id: 2, composantes: [{ libelle: "Expérience", valeur: 9, max: 20 }] }),
    ]);
    expect(lignes[0].identique).toBe(false);
    expect(lignes[0].meilleure).toBe(20);
  });

  it("conserve l'ordre du moteur plutôt que l'alphabet", () => {
    /* L'ordre des composantes porte la pondération : obligatoires d'abord,
       diplôme en dernier. Le trier détruirait cette lecture. */
    const lignes = lignesComposantes([
      candidature({
        composantes: [
          { libelle: "Compétences obligatoires", valeur: 35, max: 35 },
          { libelle: "Années d'expérience", valeur: 20, max: 20 },
        ],
      }),
    ]);
    expect(lignes.map((l) => l.libelle)).toEqual([
      "Compétences obligatoires",
      "Années d'expérience",
    ]);
  });
});

// --------------------------- Compétences ---------------------------------

describe("matriceCompetences", () => {
  const a = candidature({ id: 1, trouvees: ["python", "docker"], manquantes: ["sql"] });
  const b = candidature({ id: 2, trouvees: ["python"], manquantes: ["docker", "sql"] });

  it("reconstitue l'ensemble des compétences exigées par l'offre", () => {
    const matrice = matriceCompetences([a, b]);
    expect(matrice.map((l) => l.competence)).toEqual(["docker", "python", "sql"]);
  });

  it("relève qui détient quoi, dans l'ordre des candidatures", () => {
    const docker = matriceCompetences([a, b])[0];
    expect(docker.detentions).toEqual([true, false]);
    expect(docker.identique).toBe(false);
  });

  it("signale une compétence que personne ne détient", () => {
    /* Elle dit quelque chose de l'offre, pas des candidats : la présenter
       comme un écart reviendrait à la reprocher à chacun. */
    const sql = matriceCompetences([a, b]).find((l) => l.competence === "sql");
    expect(sql.absenteChezTous).toBe(true);
    expect(sql.identique).toBe(true);
  });

  it("trie selon l'alphabet français", () => {
    const matrice = matriceCompetences([
      candidature({ trouvees: ["zsh", "électricité"] }),
    ]);
    expect(matrice.map((l) => l.competence)).toEqual(["électricité", "zsh"]);
  });
});

// --------------------------- Assemblage ----------------------------------

describe("construireComparaison", () => {
  it("ordonne les colonnes par note décroissante", () => {
    const c = construireComparaison([
      candidature({ id: 1, nom: "Basse", score: 60 }),
      candidature({ id: 2, nom: "Haute", score: 90 }),
    ]);
    expect(c.candidatures.map((x) => x.candidate.full_name)).toEqual([
      "Haute",
      "Basse",
    ]);
  });

  it("compte les lignes qui séparent réellement les candidatures", () => {
    const c = construireComparaison([
      candidature({
        id: 1,
        trouvees: ["python"],
        composantes: [{ libelle: "Expérience", valeur: 20, max: 20 }],
      }),
      candidature({
        id: 2,
        manquantes: ["python"],
        composantes: [{ libelle: "Expérience", valeur: 9, max: 20 }],
      }),
    ]);
    expect(c.nombreDifferences).toBe(2);
  });

  it("annonce zéro différence quand la note ne départage pas", () => {
    /* Une réponse utile : elle dit au recruteur que le classement ne
       tranchera pas, et que la décision lui revient entièrement. */
    const identique = {
      trouvees: ["python"],
      composantes: [{ libelle: "Expérience", valeur: 20, max: 20 }],
    };
    const c = construireComparaison([
      candidature({ id: 1, ...identique }),
      candidature({ id: 2, ...identique }),
    ]);
    expect(c.nombreDifferences).toBe(0);
  });

  it("rapporte les critères éliminatoires à côté des composantes", () => {
    /* Un éliminatoire ne retire pas des points, il plafonne la note :
       l'écart n'est pas de degré mais de nature. */
    const c = construireComparaison([
      candidature({ id: 1 }),
      candidature({ id: 2, score: 45, eliminatoires: ["Expérience 2 ans < 3 ans requis"] }),
    ]);
    const ecartee = c.eliminatoires.find((e) => e.id === 2);
    expect(ecartee.eliminatoires).toHaveLength(1);
  });

  it("ne fabrique aucune note et n'en modifie aucune", () => {
    /* Garde-fou explicite : ce module réorganise, il ne calcule pas. */
    const entree = [candidature({ id: 1, score: 73 }), candidature({ id: 2, score: 41 })];
    const c = construireComparaison(entree);
    expect(c.candidatures.map((x) => x.score)).toEqual([73, 41]);
  });
});
