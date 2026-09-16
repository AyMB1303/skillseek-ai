/** Tests de la lecture d'un fichier protégé.
 *
 * Chaque cas correspond à une situation réellement rencontrée en livrant le
 * CV au recruteur, et non à une couverture de complaisance : c'est un type
 * mal déduit qui laissait la visionneuse blanche.
 */
import { describe, it, expect } from "vitest";
import {
  nomDepuisEntete,
  typeDuFichier,
  TYPE_PAR_DEFAUT,
} from "@/lib/telechargement";

describe("nomDepuisEntete", () => {
  it("lit un nom entre guillemets", () => {
    expect(nomDepuisEntete('inline; filename="CV-Sahri-Zaid.pdf"'))
      .toBe("CV-Sahri-Zaid.pdf");
  });

  it("lit un nom sans guillemets", () => {
    expect(nomDepuisEntete("attachment; filename=CV.pdf")).toBe("CV.pdf");
  });

  it("préfère la forme UTF-8, seule à porter les accents", () => {
    const entete = "inline; filename=\"CV.pdf\"; filename*=UTF-8''CV-Beno%C3%AEt.pdf";
    expect(nomDepuisEntete(entete)).toBe("CV-Benoît.pdf");
  });

  it("garde le nom brut si l'échappement est invalide", () => {
    expect(nomDepuisEntete("inline; filename*=UTF-8''CV-%E0%A4.pdf"))
      .toBe("CV-%E0%A4.pdf");
  });

  it("renvoie une chaîne vide en l'absence d'en-tête", () => {
    expect(nomDepuisEntete("")).toBe("");
    expect(nomDepuisEntete(null)).toBe("");
    expect(nomDepuisEntete(undefined)).toBe("");
  });

  it("renvoie une chaîne vide si l'en-tête ne nomme rien", () => {
    expect(nomDepuisEntete("inline")).toBe("");
  });
});

describe("typeDuFichier", () => {
  it("déduit le type de l'extension, source la plus sûre", () => {
    expect(typeDuFichier("CV.pdf", "")).toBe("application/pdf");
    expect(typeDuFichier("CV.docx", "")).toContain("wordprocessingml");
    expect(typeDuFichier("CV.doc", "")).toBe("application/msword");
  });

  it("ignore la casse de l'extension", () => {
    expect(typeDuFichier("CV.PDF", "")).toBe("application/pdf");
  });

  it("l'extension prime sur un Content-Type contredisant", () => {
    expect(typeDuFichier("CV.pdf", "text/html")).toBe("application/pdf");
  });

  it("retient le Content-Type annoncé quand l'extension est inconnue", () => {
    expect(typeDuFichier("piece.odt", "application/vnd.oasis.opendocument.text"))
      .toBe("application/vnd.oasis.opendocument.text");
  });

  it("écarte les paramètres du Content-Type", () => {
    expect(typeDuFichier("piece.odt", "text/plain; charset=utf-8"))
      .toBe("text/plain");
  });

  it("écarte application/octet-stream, qui ne dit rien au navigateur", () => {
    expect(typeDuFichier("piece", "application/octet-stream"))
      .toBe(TYPE_PAR_DEFAUT);
  });

  it("retombe sur le PDF quand aucune source ne renseigne", () => {
    expect(typeDuFichier("", "")).toBe(TYPE_PAR_DEFAUT);
    expect(typeDuFichier(null, null)).toBe(TYPE_PAR_DEFAUT);
  });
});
