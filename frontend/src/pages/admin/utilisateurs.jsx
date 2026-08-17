/** Administration des utilisateurs : CRUD complet, recherche, filtre par rôle. */
import { useEffect, useState, useCallback, useMemo } from "react";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur, EtatVide, Modale, useToast } from "@/components/ui";
import { useGarde, useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { retard } from "@/lib/mouvement";

const LIBELLE_ROLE = { admin: "Administrateur", recruiter: "Recruteur", candidate: "Candidat" };
const COULEUR_ROLE = {
  admin: "bg-erreur/15 text-erreur",
  recruiter: "bg-accent/15 text-accent",
  candidate: "bg-cyan/15 text-cyan",
};

export default function AdminUtilisateurs() {
  const { chargement: garde } = useGarde(["admin"]);
  const { utilisateur: moi } = useAuth();
  const { notifier } = useToast();

  const [utilisateurs, setUtilisateurs] = useState([]);
  const [roles, setRoles] = useState([]);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");
  const [recherche, setRecherche] = useState("");
  const [filtreRole, setFiltreRole] = useState("");
  const [modaleCreation, setModaleCreation] = useState(false);
  const [aSupprimer, setASupprimer] = useState(null);

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      const [u, r] = await Promise.all([api.utilisateurs(), api.roles()]);
      setUtilisateurs(u.users);
      setRoles(r.roles);
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
    }
  }, []);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  const filtres = useMemo(() => {
    const q = recherche.trim().toLowerCase();
    return utilisateurs.filter(
      (u) =>
        (!q || u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)) &&
        (!filtreRole || u.role === filtreRole)
    );
  }, [utilisateurs, recherche, filtreRole]);

  const basculerActif = async (u) => {
    const nouveau = !u.is_active;
    setUtilisateurs((l) => l.map((x) => (x.id === u.id ? { ...x, is_active: nouveau } : x)));
    try {
      await api.modifierUtilisateur(u.id, { is_active: nouveau });
      notifier(nouveau ? "Compte réactivé." : "Compte désactivé.");
    } catch (e) {
      setUtilisateurs((l) => l.map((x) => (x.id === u.id ? { ...x, is_active: u.is_active } : x)));
      notifier(e.message, { type: "erreur" });
    }
  };

  const changerRole = async (u, role) => {
    const ancien = u.role;
    setUtilisateurs((l) => l.map((x) => (x.id === u.id ? { ...x, role } : x)));
    try {
      await api.modifierUtilisateur(u.id, { role });
      notifier(`${u.full_name} est désormais ${LIBELLE_ROLE[role]?.toLowerCase()}.`);
    } catch (e) {
      setUtilisateurs((l) => l.map((x) => (x.id === u.id ? { ...x, role: ancien } : x)));
      notifier(e.message, { type: "erreur" });
    }
  };

  const supprimer = async () => {
    try {
      await api.supprimerUtilisateur(aSupprimer.id);
      setUtilisateurs((l) => l.filter((x) => x.id !== aSupprimer.id));
      notifier("Utilisateur supprimé.");
    } catch (e) {
      notifier(e.message, { type: "erreur" });
    } finally {
      setASupprimer(null);
    }
  };

  if (garde) return null;

  return (
    <Layout titre="Utilisateurs">
      <div className="flex flex-wrap gap-3 mb-5">
        <input
          type="search" className="champ max-w-xs" placeholder="Rechercher un utilisateur…"
          value={recherche} onChange={(e) => setRecherche(e.target.value)} aria-label="Rechercher"
        />
        <select className="champ max-w-[180px]" value={filtreRole} onChange={(e) => setFiltreRole(e.target.value)} aria-label="Filtrer par rôle">
          <option value="">Tous les rôles</option>
          {roles.map((r) => (
            <option key={r.id} value={r.name}>{LIBELLE_ROLE[r.name] || r.name}</option>
          ))}
        </select>
        <button onClick={() => setModaleCreation(true)} className="btn-primaire ml-auto">
          + Nouvel utilisateur
        </button>
      </div>

      {etat === "chargement" && <Chargement lignes={5} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" &&
        (filtres.length === 0 ? (
          <EtatVide titre="Aucun utilisateur" description="Aucun compte ne correspond à ces critères." />
        ) : (
          <div className="carte overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-txt2 text-xs border-b border-bordure">
                  <th className="px-5 py-3 font-medium">Utilisateur</th>
                  <th className="px-5 py-3 font-medium">Rôle</th>
                  <th className="px-5 py-3 font-medium">Actif</th>
                  <th className="px-5 py-3 font-medium">Créé le</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody>
                {filtres.map((u, rang) => (
                  <tr
                    key={u.id}
                    className="border-b border-bordure last:border-0 hover:bg-surface2/60 transition-colors entree"
                    style={{ animationDelay: retard(rang, 25, 260) }}
                  >
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-bordure text-cyan grid place-items-center text-[11px] font-bold shrink-0">
                          {u.full_name.split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <div className="font-medium truncate">
                            {u.full_name}
                            {u.id === moi?.id && <span className="text-xs text-txt2 ml-1.5">(vous)</span>}
                          </div>
                          <div className="text-xs text-txt2 truncate">{u.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3">
                      <select
                        value={u.role}
                        onChange={(e) => changerRole(u, e.target.value)}
                        disabled={u.id === moi?.id}
                        className={`chip ${COULEUR_ROLE[u.role] || "bg-bordure/50 text-txt2"} border-0 cursor-pointer disabled:cursor-not-allowed`}
                        aria-label={`Rôle de ${u.full_name}`}
                      >
                        {roles.map((r) => (
                          <option key={r.id} value={r.name} className="bg-surface text-txt">
                            {LIBELLE_ROLE[r.name] || r.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-5 py-3">
                      <button
                        onClick={() => basculerActif(u)}
                        disabled={u.id === moi?.id}
                        role="switch"
                        aria-checked={u.is_active}
                        aria-label={`Activer ou désactiver ${u.full_name}`}
                        className={`w-10 h-[22px] rounded-full transition-colors relative disabled:opacity-40 ${
                          u.is_active ? "bg-succes" : "bg-bordure"
                        }`}
                      >
                        <span
                          className={`absolute top-[3px] w-4 h-4 rounded-full bg-white transition-all ${
                            u.is_active ? "left-[22px]" : "left-[3px]"
                          }`}
                        />
                      </button>
                    </td>
                    <td className="px-5 py-3 text-txt2 text-xs">
                      {new Date(u.created_at).toLocaleDateString("fr-FR")}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={() => setASupprimer(u)}
                        disabled={u.id === moi?.id}
                        className="text-xs text-erreur hover:underline disabled:opacity-40 disabled:no-underline"
                      >
                        Supprimer
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

      <ModaleCreation
        ouverte={modaleCreation}
        roles={roles}
        onFermer={() => setModaleCreation(false)}
        onCree={(u) => {
          setUtilisateurs((l) => [...l, u]);
          notifier("Utilisateur créé.");
          setModaleCreation(false);
        }}
      />

      <Modale
        ouverte={!!aSupprimer}
        onFermer={() => setASupprimer(null)}
        titre="Confirmer la suppression"
        actions={
          <>
            <button onClick={() => setASupprimer(null)} className="btn-fantome">Annuler</button>
            <button onClick={supprimer} className="btn bg-erreur text-white hover:opacity-90">
              Supprimer définitivement
            </button>
          </>
        }
      >
        <p className="text-sm">
          Supprimer le compte de <strong>{aSupprimer?.full_name}</strong> ?
        </p>
        <p className="text-xs text-txt2 mt-2">Cette action est définitive et ne peut pas être annulée.</p>
      </Modale>
    </Layout>
  );
}

function ModaleCreation({ ouverte, roles, onFermer, onCree }) {
  const [f, setF] = useState({ full_name: "", email: "", password: "", role: "recruiter" });
  const [erreurs, setErreurs] = useState({});
  const [envoi, setEnvoi] = useState(false);

  const soumettre = async (e) => {
    e.preventDefault();
    const err = {};
    if (f.full_name.trim().length < 3) err.full_name = "Nom complet requis.";
    if (!/^[\w.+-]+@[\w-]+\.[\w.-]+$/.test(f.email)) err.email = "Email invalide.";
    if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/.test(f.password))
      err.password = "8 caractères minimum, avec majuscule, minuscule et chiffre.";
    setErreurs(err);
    if (Object.keys(err).length) return;

    setEnvoi(true);
    try {
      const d = await api.creerUtilisateur(f);
      onCree(d.user);
      setF({ full_name: "", email: "", password: "", role: "recruiter" });
    } catch (er) {
      setErreurs({ general: er.message });
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <Modale
      ouverte={ouverte}
      onFermer={onFermer}
      titre="Nouvel utilisateur"
      actions={
        <>
          <button onClick={onFermer} className="btn-fantome">Annuler</button>
          <button onClick={soumettre} disabled={envoi} className="btn-primaire">
            {envoi ? "Création…" : "Créer le compte"}
          </button>
        </>
      }
    >
      <form onSubmit={soumettre} className="space-y-4" noValidate>
        {erreurs.general && <p className="text-sm text-erreur">{erreurs.general}</p>}
        {[
          { cle: "full_name", label: "Nom complet", type: "text" },
          { cle: "email", label: "Adresse email", type: "email" },
          { cle: "password", label: "Mot de passe provisoire", type: "password" },
        ].map((c) => (
          <div key={c.cle}>
            <label htmlFor={c.cle} className="etiquette">{c.label}</label>
            <input
              id={c.cle} type={c.type} className={`champ ${erreurs[c.cle] ? "border-erreur" : ""}`}
              value={f[c.cle]} onChange={(e) => setF({ ...f, [c.cle]: e.target.value })}
            />
            {erreurs[c.cle] && <p className="text-xs text-erreur mt-1.5">{erreurs[c.cle]}</p>}
          </div>
        ))}
        <div>
          <label htmlFor="role" className="etiquette">Rôle</label>
          <select id="role" className="champ" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
            {roles.map((r) => (
              <option key={r.id} value={r.name}>{LIBELLE_ROLE[r.name] || r.name}</option>
            ))}
          </select>
        </div>
      </form>
    </Modale>
  );
}
