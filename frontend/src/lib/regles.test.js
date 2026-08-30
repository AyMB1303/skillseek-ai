/** Tests des règles de l'interface.
 *
 * Ces règles décidaient jusqu'ici du comportement d'écrans entiers sans être
 * vérifiées : elles vivaient à l'intérieur des composants, où seul un test de
 * rendu complet aurait pu les atteindre. Sorties dans un module, elles se
 * testent directement.
 *
 * Chaque cas correspond à une situation rencontrée pendant le développement,
 * et non à une couverture de complaisance.
 */
import { describe, it, expect } from "vitest";
import {
  memesDroits,
  comparerFr,
  trierFr,
  competencesDisponibles,
  filtreActif,
  classer,
  SEUIL_PRESELECTION,
  PLAFOND_PRESELECTION,
} from "./regles";

describe("memesDroits — égalité d'ensembles de permissions", () => {
  it("reconnaît deux listes identiques", () => {
    expect(memesDroits(["a", "b"], ["a", "b"])).toBe(true);
  });

  it("ignore l'ordre : c'est un ensemble, pas une séquence", () => {
    expect(memesDroits(["b", "a"], ["a", "b"])).toBe(true);
  });

  it("distingue deux ensembles différents", () => {
    expect(memesDroits(["a"], ["a", "b"])).toBe(false);
  });

  it("reste juste si un code est répété", () => {
    // Le piège de la comparaison par longueur seule : ["a","a"] et ["a","b"]
    // ont la même taille sans désigner le même ensemble.
    expect(memesDroits(["a", "a"], ["a", "b"])).toBe(false);
  });

  it("traite l'absence de liste comme un ensemble vide", () => {
    expect(memesDroits(null, [])).toBe(true);
    expect(memesDroits(undefined, ["a"])).toBe(false);
  });
});

describe("comparerFr — l'ordre du dictionnaire français", () => {
  it("range un mot accentué à sa place, non en fin de liste", () => {
    // Le tri par défaut compare les codes Unicode : « électricité » (0xE9)
    // passerait après « zsh » (0x7A). C'est le défaut que ce comparateur
    // corrige.
    expect(comparerFr("électricité", "zsh")).toBeLessThan(0);
  });

  it("ordonne normalement deux mots non accentués", () => {
    expect(comparerFr("python", "sql")).toBeLessThan(0);
  });

  it("rend zéro pour deux libellés identiques", () => {
    expect(comparerFr("docker", "docker")).toBe(0);
  });
});

describe("trierFr", () => {
  it("place les accents à leur rang alphabétique", () => {
    expect(trierFr(["zsh", "électricité", "python"])).toEqual([
      "électricité",
      "python",
      "zsh",
    ]);
  });

  it("ne modifie pas la liste reçue", () => {
    const origine = ["b", "a"];
    trierFr(origine);
    expect(origine).toEqual(["b", "a"]);
  });

  it("accepte une liste absente", () => {
    expect(trierFr(undefined)).toEqual([]);
  });
});

describe("competencesDisponibles — filtres qui donnent un résultat", () => {
  const lot = [
    { score_details: { profil_ats: { skills: ["python", "sql"] } } },
    { score_details: { profil_ats: { skills: ["sql", "docker"] } } },
  ];

  it("réunit les compétences sans doublon et les trie", () => {
    expect(competencesDisponibles(lot)).toEqual(["docker", "python", "sql"]);
  });

  it("traverse sans erreur une candidature non encore analysée", () => {
    expect(competencesDisponibles([{}, ...lot])).toEqual([
      "docker",
      "python",
      "sql",
    ]);
  });

  it("rend une liste vide plutôt que d'échouer sur une entrée vide", () => {
    expect(competencesDisponibles([])).toEqual([]);
    expect(competencesDisponibles(null)).toEqual([]);
  });
});

describe("filtreActif — éviter la valeur qui fuit dans la page", () => {
  it("détecte au moins un filtre renseigné", () => {
    expect(filtreActif("", "python")).toBe(true);
  });

  it("rend faux quand aucun filtre n'est posé", () => {
    expect(filtreActif("", null, undefined)).toBe(false);
  });

  it("rend un booléen, jamais la valeur elle-même", () => {
    // En JSX, `{0 && <Bandeau/>}` affiche « 0 » dans la page. C'est
    // exactement ce que cette conversion empêche.
    expect(filtreActif(0)).toBe(false);
    expect(typeof filtreActif("x")).toBe("boolean");
  });
});

describe("classer — la règle de présélection RG-01", () => {
  it("écarte une note strictement inférieure au seuil", () => {
    expect(classer(SEUIL_PRESELECTION - 1, 0)).toBe("ecartee");
  });

  it("retient une note égale au seuil", () => {
    // Le seuil est inclusif : « écartée en dessous de 50 », donc 50 passe.
    expect(classer(SEUIL_PRESELECTION, 0)).toBe("preselectionnee");
  });

  it("présélectionne dans la limite du plafond", () => {
    expect(classer(90, PLAFOND_PRESELECTION - 1)).toBe("preselectionnee");
  });

  it("retient hors présélection au-delà du plafond", () => {
    expect(classer(90, PLAFOND_PRESELECTION)).toBe("retenue");
  });

  it("distingue une candidature non encore analysée d'une note nulle", () => {
    expect(classer(null)).toBe("en_attente");
    expect(classer(0, 0)).toBe("ecartee");
  });
});
