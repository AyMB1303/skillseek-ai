/** Contexte d'authentification : utilisateur courant, connexion, déconnexion, garde de route. */
import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useRouter } from "next/router";
import { api, jetons } from "./api";

const ContexteAuth = createContext(null);

// Page d'accueil selon le rôle : chacun arrive sur son écran utile.
export const ACCUEIL_PAR_ROLE = {
  admin: "/admin/utilisateurs",
  recruiter: "/dashboard",
  candidate: "/offres",
};

export function FournisseurAuth({ children }) {
  const [utilisateur, setUtilisateur] = useState(null);
  const [chargement, setChargement] = useState(true);
  const router = useRouter();

  useEffect(() => {
    if (!jetons.lireAccess()) {
      setChargement(false);
      return;
    }
    api
      .moi()
      .then((d) => setUtilisateur(d.user))
      .catch(() => jetons.effacer())
      .finally(() => setChargement(false));
  }, []);

  const connexion = useCallback(
    async (email, motDePasse) => {
      const d = await api.connexion(email, motDePasse);
      jetons.enregistrer(d.access_token, d.refresh_token);
      setUtilisateur(d.user);
      router.push(ACCUEIL_PAR_ROLE[d.user.role] || "/");
      return d.user;
    },
    [router]
  );

  const deconnexion = useCallback(async () => {
    try {
      await api.deconnexion();
    } catch {
      /* le token peut déjà être invalide : on nettoie quand même */
    }
    jetons.effacer();
    setUtilisateur(null);
    router.push("/connexion");
  }, [router]);

  return (
    <ContexteAuth.Provider value={{ utilisateur, chargement, connexion, deconnexion, setUtilisateur }}>
      {children}
    </ContexteAuth.Provider>
  );
}

export const useAuth = () => useContext(ContexteAuth);

/** Protège une page : redirige si non connecté ou si le rôle n'est pas autorisé. */
export function useGarde(rolesAutorises) {
  const { utilisateur, chargement } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (chargement) return;
    if (!utilisateur) {
      router.replace("/connexion");
    } else if (rolesAutorises && !rolesAutorises.includes(utilisateur.role)) {
      router.replace(ACCUEIL_PAR_ROLE[utilisateur.role] || "/");
    }
  }, [utilisateur, chargement, rolesAutorises, router]);

  return { utilisateur, chargement: chargement || !utilisateur };
}
