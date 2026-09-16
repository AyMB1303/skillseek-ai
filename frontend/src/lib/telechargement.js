/** Règles de lecture d'un fichier protégé renvoyé par l'API.
 *
 * Ces deux fonctions décidaient du sort du CV depuis l'intérieur de
 * `api.js`, où seul un test de bout en bout aurait pu les atteindre — et
 * elles ne sont pas anodines : un type mal déduit, et le lecteur PDF intégré
 * du navigateur refuse d'afficher le document. Le recruteur se retrouve
 * devant un cadre vide, sans pouvoir confronter le profil extrait au CV.
 *
 * Sorties ici, elles se vérifient directement, comme les règles d'interface
 * l'ont été avant elles.
 */

/** Types que l'extension permet d'affirmer, quoi qu'annonce le serveur. */
export const TYPES_PAR_EXTENSION = {
  pdf: "application/pdf",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  doc: "application/msword",
};

/** Type retenu par défaut : les CV déposés sont en très large majorité des PDF. */
export const TYPE_PAR_DEFAUT = "application/pdf";

/**
 * Nom du fichier, lu dans l'en-tête `Content-Disposition`.
 *
 * La forme `filename*=UTF-8''...` est examinée en premier : c'est celle qui
 * porte les accents, et un nom français s'y trouve plus souvent que dans la
 * forme simple, qui ne sait pas les représenter.
 */
export function nomDepuisEntete(entete) {
  if (!entete) return "";

  const etendu = /filename\*=UTF-8''([^;]+)/i.exec(entete);
  if (etendu) {
    try {
      return decodeURIComponent(etendu[1]);
    } catch {
      // Séquence d'échappement invalide : le nom brut vaut mieux que rien.
      return etendu[1];
    }
  }

  const simple = /filename="([^"]*)"/i.exec(entete);
  if (simple) return simple[1];

  const nu = /filename=([^;]+)/i.exec(entete);
  return nu ? nu[1].trim() : "";
}

/**
 * Type du document, de la source la plus sûre à la moins sûre.
 *
 * L'extension prime : elle vient du nom que le serveur a lui-même composé à
 * partir du fichier stocké. Vient ensuite le `Content-Type` annoncé, sauf
 * s'il est générique — `application/octet-stream` ne dit rien d'autre que
 * « des octets », et le navigateur n'en ferait rien.
 */
export function typeDuFichier(nom, contentType) {
  const extension = (nom || "").split(".").pop().toLowerCase();
  if (TYPES_PAR_EXTENSION[extension]) return TYPES_PAR_EXTENSION[extension];

  const annonce = (contentType || "").split(";")[0].trim();
  if (annonce && annonce !== "application/octet-stream") return annonce;

  return TYPE_PAR_DEFAUT;
}
