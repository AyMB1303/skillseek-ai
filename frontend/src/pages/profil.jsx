/** Profil : identité, mot de passe, et droits sur les données (RGPD / loi 09-08). */
import { useState } from "react";
import Layout from "@/components/Layout";
import { Modale, useToast } from "@/components/ui";
import { useGarde, useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

const LIBELLE_ROLE = { admin: "Administrateur", recruiter: "Recruteur", candidate: "Candidat" };

export default function Profil() {
  const { chargement: garde } = useGarde();
  const { utilisateur, setUtilisateur, deconnexion } = useAuth();
  const { notifier } = useToast();

  const [nom, setNom] = useState(utilisateur?.full_name || "");
  const [enregNom, setEnregNom] = useState(false);
  const [mdp, setMdp] = useState({ actuel: "", nouveau: "", confirmation: "" });
  const [erreursMdp, setErreursMdp] = useState({});
  const [enregMdp, setEnregMdp] = useState(false);
  const [modaleSuppr, setModaleSuppr] = useState(false);

  if (garde) return null;

  const initiales = (utilisateur?.full_name || "?")
    .split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase();

  const enregistrerNom = async (e) => {
    e.preventDefault();
    setEnregNom(true);
    try {
      const d = await api.modifierProfil({ full_name: nom });
      setUtilisateur(d.user);
      notifier("Profil mis à jour.");
    } catch (err) {
      notifier(err.details?.full_name || err.message, { type: "erreur" });
    } finally {
      setEnregNom(false);
    }
  };

  const enregistrerMdp = async (e) => {
    e.preventDefault();
    const err = {};
    if (!mdp.actuel) err.current_password = "Saisissez votre mot de passe actuel.";
    if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/.test(mdp.nouveau))
      err.new_password = "8 caractères minimum, avec majuscule, minuscule et chiffre.";
    if (mdp.nouveau !== mdp.confirmation) err.confirmation = "Les mots de passe ne correspondent pas.";
    setErreursMdp(err);
    if (Object.keys(err).length) return;

    setEnregMdp(true);
    try {
      await api.changerMotDePasse(mdp.actuel, mdp.nouveau);
      setMdp({ actuel: "", nouveau: "", confirmation: "" });
      notifier("Mot de passe modifié.");
    } catch (er) {
      setErreursMdp(er.details || { general: er.message });
    } finally {
      setEnregMdp(false);
    }
  };

  const telecharger = async () => {
    try {
      const d = await api.exporterDonnees();
      const blob = new Blob([JSON.stringify(d, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "mes-donnees-skillseek.json";
      a.click();
      URL.revokeObjectURL(url);
      notifier("Vos données ont été téléchargées.");
    } catch (e) {
      notifier(e.message, { type: "erreur" });
    }
  };

  const supprimerCompte = async () => {
    try {
      await api.supprimerCompte();
      notifier("Compte supprimé.");
      deconnexion();
    } catch (e) {
      notifier(e.message, { type: "erreur" });
      setModaleSuppr(false);
    }
  };

  return (
    <Layout titre="Mon profil">
      <div className="max-w-2xl space-y-5">
        {/* Identité */}
        <section className="carte p-6 flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-accent to-cyan grid place-items-center text-lg font-bold text-fond shrink-0">
            {initiales}
          </div>
          <div className="min-w-0">
            <h2 className="text-lg font-bold truncate">{utilisateur?.full_name}</h2>
            <p className="text-sm text-txt2 truncate">{utilisateur?.email}</p>
            <span className="chip bg-accent/15 text-accent mt-2">
              {LIBELLE_ROLE[utilisateur?.role] || utilisateur?.role}
            </span>
          </div>
        </section>

        {/* Nom */}
        <form onSubmit={enregistrerNom} className="carte p-6 space-y-4">
          <h2 className="font-semibold text-sm">Informations personnelles</h2>
          <div>
            <label htmlFor="nom" className="etiquette">Nom complet</label>
            <input id="nom" className="champ" value={nom} onChange={(e) => setNom(e.target.value)} />
          </div>
          <div>
            <label htmlFor="mail" className="etiquette">Adresse email</label>
            <input id="mail" className="champ opacity-60" value={utilisateur?.email || ""} disabled />
            <p className="text-[11px] text-txt2 mt-1.5">
              L'adresse email ne peut pas être modifiée. Contactez un administrateur si nécessaire.
            </p>
          </div>
          <button
            type="submit"
            disabled={enregNom || nom.trim() === utilisateur?.full_name}
            className="btn-primaire"
          >
            {enregNom ? "Enregistrement…" : "Enregistrer"}
          </button>
        </form>

        {/* Mot de passe */}
        <form onSubmit={enregistrerMdp} className="carte p-6 space-y-4" noValidate>
          <h2 className="font-semibold text-sm">Changer le mot de passe</h2>
          {erreursMdp.general && <p className="text-sm text-erreur">{erreursMdp.general}</p>}

          {[
            { cle: "actuel", champErreur: "current_password", label: "Mot de passe actuel" },
            { cle: "nouveau", champErreur: "new_password", label: "Nouveau mot de passe" },
            { cle: "confirmation", champErreur: "confirmation", label: "Confirmer le nouveau mot de passe" },
          ].map((c) => (
            <div key={c.cle}>
              <label htmlFor={c.cle} className="etiquette">{c.label}</label>
              <input
                id={c.cle} type="password"
                className={`champ ${erreursMdp[c.champErreur] ? "border-erreur" : ""}`}
                value={mdp[c.cle]} onChange={(e) => setMdp({ ...mdp, [c.cle]: e.target.value })}
                autoComplete={c.cle === "actuel" ? "current-password" : "new-password"}
              />
              {erreursMdp[c.champErreur] && (
                <p className="text-xs text-erreur mt-1.5">{erreursMdp[c.champErreur]}</p>
              )}
            </div>
          ))}

          <button type="submit" disabled={enregMdp} className="btn-primaire">
            {enregMdp ? "Modification…" : "Modifier le mot de passe"}
          </button>
        </form>

        {/* Données personnelles */}
        <section className="carte p-6 space-y-4">
          <div>
            <h2 className="font-semibold text-sm">Mes données personnelles</h2>
            <p className="text-xs text-txt2 mt-1 leading-snug">
              Conformément à la loi 09-08 et aux principes du RGPD, vous pouvez accéder à vos données
              et demander leur suppression à tout moment.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={telecharger} className="btn-secondaire">Télécharger mes données</button>
            {utilisateur?.role !== "admin" && (
              <button onClick={() => setModaleSuppr(true)} className="btn-fantome text-erreur hover:bg-erreur/10">
                Supprimer mon compte
              </button>
            )}
          </div>
        </section>
      </div>

      <Modale
        ouverte={modaleSuppr}
        onFermer={() => setModaleSuppr(false)}
        titre="Supprimer définitivement votre compte"
        actions={
          <>
            <button onClick={() => setModaleSuppr(false)} className="btn-fantome">Annuler</button>
            <button onClick={supprimerCompte} className="btn bg-erreur text-white hover:opacity-90">
              Supprimer mon compte
            </button>
          </>
        }
      >
        <p className="text-sm">
          Votre compte et l'ensemble de vos candidatures seront définitivement supprimés.
        </p>
        <p className="text-xs text-txt2 mt-2">Cette action est irréversible.</p>
      </Modale>
    </Layout>
  );
}
