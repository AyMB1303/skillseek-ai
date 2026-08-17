/**
 * Profil : ce que je suis sur la plateforme, et ce que je maîtrise.
 *
 * La page se contentait de trois formulaires. Elle répondait donc à
 * « comment changer mon mot de passe ? » et à rien d'autre — alors qu'un
 * espace personnel devrait d'abord répondre à « où en suis-je ? ».
 *
 * Elle s'ouvre désormais sur une activité chiffrée, différente selon le rôle
 * parce que la question l'est aussi : le candidat veut savoir où en sont ses
 * candidatures, le recruteur ce que ses offres ont produit, l'administrateur
 * ce qui attend sa décision. Les chiffres viennent des mêmes routes que les
 * tableaux de bord — aucune donnée n'est recalculée ici.
 *
 * Les réglages restent, mais après. On ne change pas son mot de passe tous
 * les jours ; on veut voir son activité à chaque visite.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { Modale, useToast } from "@/components/ui";
import { useGarde, useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { useCompteur, retard } from "@/lib/mouvement";

const LIBELLE_ROLE = { admin: "Administrateur", recruiter: "Recruteur", candidate: "Candidat" };

const LIBELLE_STATUT = {
  received: "Reçue",
  under_review: "En étude",
  shortlisted: "Présélectionnée",
  interview: "Entretien",
  hired: "Recrutement",
  rejected: "Non retenue",
};

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
      <div className="max-w-4xl space-y-5">

        {/* ---------------- Identité ---------------- */}
        <section className="carte p-6 flex flex-wrap items-center gap-4 entree">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-accent to-cyan grid place-items-center text-lg font-bold text-fond shrink-0">
            {initiales}
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-bold truncate">{utilisateur?.full_name}</h2>
            <p className="text-sm text-txt2 truncate">{utilisateur?.email}</p>
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <span className="chip bg-accent/15 text-accent">
                {LIBELLE_ROLE[utilisateur?.role] || utilisateur?.role}
              </span>
              {utilisateur?.company && (
                <span className="chip bg-bordure/50 text-txt2">{utilisateur.company}</span>
              )}
              {utilisateur?.created_at && (
                <span className="text-[11.5px] text-txt2">
                  Membre depuis {new Date(utilisateur.created_at).toLocaleDateString("fr-FR", {
                    month: "long", year: "numeric",
                  })}
                </span>
              )}
            </div>
          </div>
        </section>

        {/* ---------------- Activité ---------------- */}
        <Activite role={utilisateur?.role} />

        <div className="grid gap-5 lg:grid-cols-2 items-start">
          {/* ---------------- Identité modifiable ---------------- */}
          <form onSubmit={enregistrerNom} className="carte p-6 space-y-4 entree"
                style={{ animationDelay: retard(1, 60) }}>
            <h2 className="font-semibold text-sm">Informations personnelles</h2>
            <div>
              <label htmlFor="nom" className="etiquette">Nom complet</label>
              <input id="nom" className="champ" value={nom} onChange={(e) => setNom(e.target.value)} />
            </div>
            <div>
              <label htmlFor="mail" className="etiquette">Adresse email</label>
              <input id="mail" className="champ opacity-60" value={utilisateur?.email || ""} disabled />
              <p className="text-[11px] text-txt2 mt-1.5">
                L'adresse identifie le compte et sert aux notifications : elle ne peut pas être
                modifiée depuis cet écran. Un administrateur peut le faire.
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

          {/* ---------------- Mot de passe ---------------- */}
          <form onSubmit={enregistrerMdp} className="carte p-6 space-y-4 entree"
                style={{ animationDelay: retard(2, 60) }} noValidate>
            <div>
              <h2 className="font-semibold text-sm">Changer le mot de passe</h2>
              <p className="text-[11px] text-txt2 mt-1 leading-snug">
                Il est conservé sous forme d'empreinte et ne peut être relu par personne, pas
                même par un administrateur. Cinq tentatives infructueuses verrouillent le compte
                dix minutes et vous en avertissent.
              </p>
            </div>
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
        </div>

        {/* ---------------- Données personnelles ---------------- */}
        <section className="carte p-6 space-y-4 entree" style={{ animationDelay: retard(3, 60) }}>
          <div>
            <h2 className="font-semibold text-sm">Mes données personnelles</h2>
            <p className="text-xs text-txt2 mt-1 leading-relaxed max-w-2xl">
              Conformément à la loi 09-08 et aux principes du RGPD, vous pouvez à tout moment
              obtenir une copie de vos données ou en demander l'effacement. Le fichier
              téléchargé contient votre compte et l'ensemble de vos candidatures — offre visée,
              statut, date de dépôt.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={telecharger} className="btn-secondaire">
              Télécharger mes données
            </button>
            {utilisateur?.role !== "admin" && (
              <button
                onClick={() => setModaleSuppr(true)}
                className="btn-fantome text-erreur hover:bg-erreur/10"
              >
                Supprimer mon compte
              </button>
            )}
          </div>
          {utilisateur?.role === "admin" && (
            <p className="text-[11px] text-txt2">
              Un compte administrateur ne peut pas être supprimé depuis cet écran : la
              plateforme deviendrait ingérable s'il était le dernier.
            </p>
          )}
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

/* ------------------------------------------------------------------ */
/* Activité                                                            */
/* ------------------------------------------------------------------ */

/**
 * Chiffres d'activité, propres au rôle.
 *
 * Chaque rôle interroge la route qui le concerne, et une seule : le candidat
 * ne détient pas les droits du tableau de bord, l'administrateur ne détient
 * pas ceux des candidatures. Un échec reste silencieux — l'activité est un
 * complément, son absence ne doit pas empêcher de changer son mot de passe.
 */
function Activite({ role }) {
  const [donnees, setDonnees] = useState(null);
  const [vide, setVide] = useState(false);

  const charger = useCallback(async () => {
    try {
      if (role === "candidate") {
        const d = await api.mesCandidatures();
        const liste = d.applications || [];
        setVide(liste.length === 0);
        setDonnees({
          lien: "/mes-candidatures",
          libelleLien: "Suivre mes candidatures",
          cartes: [
            { libelle: "Candidatures déposées", valeur: liste.length },
            {
              libelle: "En cours d'examen",
              valeur: liste.filter((c) =>
                ["received", "under_review", "shortlisted"].includes(c.status)
              ).length,
              accent: "accent",
            },
            {
              libelle: "Entretiens",
              valeur: liste.filter((c) => c.status === "interview").length,
              accent: "alerte",
            },
            {
              libelle: "Décisions rendues",
              valeur: liste.filter((c) => ["hired", "rejected"].includes(c.status)).length,
              accent: "succes",
            },
          ],
          derniere: liste[0],
        });
      } else if (role === "recruiter") {
        const d = await api.statistiques(90);
        setDonnees({
          lien: "/dashboard",
          libelleLien: "Ouvrir le tableau de bord",
          periode: "sur les 90 derniers jours",
          cartes: [
            { libelle: "Offres ouvertes", valeur: d.offres_ouvertes },
            { libelle: "Candidatures reçues", valeur: d.kpi.recues.valeur, accent: "accent" },
            { libelle: "Entretiens", valeur: d.kpi.entretiens.valeur, accent: "alerte" },
            { libelle: "Recrutements", valeur: d.kpi.recrutes.valeur, accent: "succes" },
          ],
        });
      } else if (role === "admin") {
        const d = await api.statistiquesAdmin();
        setDonnees({
          lien: "/admin",
          libelleLien: "Ouvrir l'administration",
          cartes: [
            { libelle: "Comptes actifs", valeur: d.comptes.total },
            { libelle: "En attente de validation", valeur: d.comptes.en_attente, accent: "alerte" },
            { libelle: "Offres publiées", valeur: d.offres.total, accent: "accent" },
            { libelle: "Éléments en corbeille", valeur: d.corbeille.total },
          ],
        });
      }
    } catch {
      /* L'activité est un complément : son absence ne bloque rien. */
    }
  }, [role]);

  useEffect(() => {
    charger();
  }, [charger]);

  if (!donnees) return null;

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold text-sm">
          Mon activité
          {donnees.periode && (
            <span className="font-normal text-txt2"> {donnees.periode}</span>
          )}
        </h2>
        <Link href={donnees.lien} className="text-[12.5px] text-accent hover:text-cyan">
          {donnees.libelleLien} →
        </Link>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {donnees.cartes.map((c, i) => (
          <CarteChiffre key={c.libelle} {...c} rang={i} />
        ))}
      </div>

      {vide && (
        <p className="text-[12.5px] text-txt2">
          Vous n'avez pas encore postulé.{" "}
          <Link href="/offres" className="text-accent hover:text-cyan">
            Parcourir les offres
          </Link>
        </p>
      )}

      {donnees.derniere && (
        <p className="text-[12.5px] text-txt2">
          Dernière candidature :{" "}
          <span className="text-txt">{donnees.derniere.offer?.title}</span>
          {" — "}
          {LIBELLE_STATUT[donnees.derniere.status] || donnees.derniere.status}
        </p>
      )}
    </section>
  );
}

function CarteChiffre({ libelle, valeur, accent, rang = 0 }) {
  const couleurs = {
    accent: "text-accent", alerte: "text-alerte", succes: "text-succes", cyan: "text-cyan",
  };
  const affiche = useCompteur(valeur ?? 0, { duree: 700 });
  return (
    <div
      className="carte carte-reactive p-4 entree"
      style={{ animationDelay: retard(rang, 60) }}
    >
      <p
        className={`text-2xl font-bold tabular-nums ${couleurs[accent] || "text-txt"}`}
        aria-label={`${libelle} : ${valeur}`}
      >
        {affiche}
      </p>
      <p className="text-[11.5px] text-txt2 mt-0.5 leading-snug">{libelle}</p>
    </div>
  );
}
