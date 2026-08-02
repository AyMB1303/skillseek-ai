/**
 * Client API : centralise les appels au backend Flask.
 * Gère l'ajout du JWT, le rafraîchissement automatique du token expiré,
 * et la remontée d'erreurs lisibles côté interface.
 */
const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000/api";

const CLE_ACCESS = "skillseek_access";
const CLE_REFRESH = "skillseek_refresh";

export const jetons = {
  lireAccess: () => (typeof window === "undefined" ? null : localStorage.getItem(CLE_ACCESS)),
  lireRefresh: () => (typeof window === "undefined" ? null : localStorage.getItem(CLE_REFRESH)),
  enregistrer: (access, refresh) => {
    localStorage.setItem(CLE_ACCESS, access);
    if (refresh) localStorage.setItem(CLE_REFRESH, refresh);
  },
  effacer: () => {
    localStorage.removeItem(CLE_ACCESS);
    localStorage.removeItem(CLE_REFRESH);
  },
};

export class ErreurApi extends Error {
  constructor(message, statut, details) {
    super(message);
    this.statut = statut;
    this.details = details;
  }
}

async function rafraichir() {
  const refresh = jetons.lireRefresh();
  if (!refresh) return false;
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    headers: { Authorization: `Bearer ${refresh}` },
  });
  if (!res.ok) return false;
  const data = await res.json();
  jetons.enregistrer(data.access_token);
  return true;
}

/**
 * Télécharge un fichier protégé et renvoie une URL locale (blob).
 * Nécessaire car une balise <a href> n'envoie pas l'en-tête Authorization.
 */
export async function telechargerFichier(chemin) {
  const token = jetons.lireAccess();
  const res = await fetch(`${BASE}${chemin}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const texte = await res.text();
    let message = "Fichier indisponible.";
    try {
      message = JSON.parse(texte)?.error || message;
    } catch {
      /* réponse non JSON : on garde le message par défaut */
    }
    throw new ErreurApi(message, res.status);
  }
  return URL.createObjectURL(await res.blob());
}

export async function appel(chemin, { method = "GET", body, formData, reessai = true } = {}) {
  const entetes = {};
  const token = jetons.lireAccess();
  if (token) entetes.Authorization = `Bearer ${token}`;
  if (body) entetes["Content-Type"] = "application/json";

  let res;
  try {
    res = await fetch(`${BASE}${chemin}`, {
      method,
      headers: entetes,
      body: formData || (body ? JSON.stringify(body) : undefined),
    });
  } catch {
    throw new ErreurApi("Serveur injoignable. Vérifiez que l'API est démarrée.", 0);
  }

  // Token expiré : on tente un rafraîchissement transparent, une seule fois.
  if (res.status === 401 && reessai && jetons.lireRefresh()) {
    if (await rafraichir()) return appel(chemin, { method, body, formData, reessai: false });
    jetons.effacer();
    if (typeof window !== "undefined") window.location.href = "/connexion";
  }

  const texte = await res.text();
  const data = texte ? JSON.parse(texte) : null;

  if (!res.ok) {
    throw new ErreurApi(
      data?.error || "Une erreur est survenue.",
      res.status,
      data?.errors || data?.missing_permissions
    );
  }
  return data;
}

export const api = {
  // Authentification
  connexion: (email, password) => appel("/auth/login", { method: "POST", body: { email, password } }),
  inscription: (donnees) => appel("/auth/register", { method: "POST", body: donnees }),
  moi: () => appel("/auth/me"),
  deconnexion: () => appel("/auth/logout", { method: "POST" }),

  // Offres
  offres: () => appel("/offers"),
  offre: (id) => appel(`/offers/${id}`),
  creerOffre: (donnees) => appel("/offers", { method: "POST", body: donnees }),
  modifierOffre: (id, donnees) => appel(`/offers/${id}`, { method: "PATCH", body: donnees }),

  // Candidatures
  candidatures: (params = "") => appel(`/applications${params}`),
  mesCandidatures: () => appel("/applications/mine"),
  candidaturesOffre: (offreId) => appel(`/applications?offer_id=${offreId}`),
  changerStatut: (id, statut) => appel(`/applications/${id}/status`, { method: "PATCH", body: { status: statut } }),
  analyser: (id, profil) => appel(`/applications/${id}/analyze`, { method: "POST", body: profil }),
  postuler: (offreId, fichier) => {
    const fd = new FormData();
    fd.append("cv", fichier);
    fd.append("offer_id", offreId);
    return appel("/applications", { method: "POST", formData: fd });
  },

  // Tableau de bord
  statistiques: (periode = 30) => appel(`/dashboard/stats?days=${periode}`),

  // Notifications
  notifications: () => appel("/notifications"),
  marquerLue: (id) => appel(`/notifications/${id}/read`, { method: "POST" }),
  marquerToutesLues: () => appel("/notifications/read-all", { method: "POST" }),

  // Profil
  modifierProfil: (d) => appel("/profile", { method: "PATCH", body: d }),
  changerMotDePasse: (actuel, nouveau) =>
    appel("/profile/password", { method: "POST", body: { current_password: actuel, new_password: nouveau } }),
  exporterDonnees: () => appel("/profile/data"),
  supprimerCompte: () => appel("/profile", { method: "DELETE" }),

  // Administration
  utilisateurs: () => appel("/users"),
  creerUtilisateur: (d) => appel("/users", { method: "POST", body: d }),
  modifierUtilisateur: (id, d) => appel(`/users/${id}`, { method: "PATCH", body: d }),
  supprimerUtilisateur: (id) => appel(`/users/${id}`, { method: "DELETE" }),
  roles: () => appel("/roles"),
  permissions: () => appel("/permissions"),
  definirPermissions: (roleId, codes) =>
    appel(`/roles/${roleId}/permissions`, { method: "PUT", body: { permissions: codes } }),
};
