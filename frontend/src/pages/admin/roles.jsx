/** Rôles & permissions : matrice de droits, application immédiate (RG-02). */
import { useEffect, useState, useCallback } from "react";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur, useToast } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";
import { retard } from "@/lib/mouvement";

const LIBELLE_ROLE = { admin: "Administrateur", recruiter: "Recruteur", candidate: "Candidat" };

// Descriptions lisibles : l'administrateur doit comprendre ce qu'il accorde.
const DESCRIPTIONS = {
  manage_users: "Créer, modifier et supprimer les comptes utilisateurs",
  manage_roles: "Gérer les rôles et attribuer les permissions",
  manage_offers: "Créer et modifier les offres d'emploi",
  view_applications: "Consulter toutes les candidatures et leurs scores",
  manage_applications: "Changer le statut des candidatures",
  view_dashboard: "Accéder au tableau de bord décisionnel",
  use_chatbot: "Utiliser l'assistant RH",
};

export default function AdminRoles() {
  const { chargement: garde } = useGarde(["admin"]);
  const { notifier } = useToast();

  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [selection, setSelection] = useState(null);
  const [cochees, setCochees] = useState([]);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");
  const [envoi, setEnvoi] = useState(false);

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      const [r, p] = await Promise.all([api.roles(), api.permissions()]);
      setRoles(r.roles);
      setPermissions(p.permissions);
      const premier = r.roles[0];
      setSelection(premier || null);
      setCochees(premier?.permissions || []);
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
    }
  }, []);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  const choisirRole = (r) => {
    setSelection(r);
    setCochees(r.permissions || []);
  };

  const basculer = (code) =>
    setCochees((c) => (c.includes(code) ? c.filter((x) => x !== code) : [...c, code]));

  // Deux listes de codes désignent-elles le même ensemble de droits ?
  // Comparer des tableaux triés puis sérialisés donnerait le bon résultat,
  // mais dirait mal l'intention : ce qui compte ici n'est pas un ordre, c'est
  // une égalité d'ensembles. La comparaison des tailles précède la vérification
  // d'inclusion pour rester juste même si un code apparaissait deux fois.
  const memesDroits = (a, b) => {
    const gauche = new Set(a);
    const droite = new Set(b);
    return gauche.size === droite.size && [...gauche].every((code) => droite.has(code));
  };

  const modifie = Boolean(selection) && !memesDroits(cochees, selection?.permissions || []);

  const enregistrer = async () => {
    setEnvoi(true);
    try {
      const d = await api.definirPermissions(selection.id, cochees);
      setRoles((l) => l.map((r) => (r.id === d.role.id ? d.role : r)));
      setSelection(d.role);
      notifier("Permissions mises à jour. Effet immédiat pour tous les utilisateurs de ce rôle.");
    } catch (e) {
      notifier(e.message, { type: "erreur" });
    } finally {
      setEnvoi(false);
    }
  };

  if (garde) return null;

  return (
    <Layout titre="Rôles & permissions">
      {etat === "chargement" && <Chargement lignes={4} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" && (
        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-5">
          {/* Liste des rôles */}
          <aside className="carte overflow-hidden h-fit">
            <h2 className="px-4 py-3 text-xs font-semibold text-txt2 uppercase tracking-wide border-b border-bordure">
              Rôles
            </h2>
            {roles.map((r, rang) => (
              <button
                key={r.id}
                style={{ animationDelay: retard(rang, 70) }}
                onClick={() => choisirRole(r)}
                className={`w-full text-left px-4 py-3 border-b border-bordure last:border-0 transition-colors entree ${
                  selection?.id === r.id ? "bg-accent/10 border-l-2 border-l-accent" : "hover:bg-surface2/60"
                }`}
                aria-current={selection?.id === r.id}
              >
                <p className="text-sm font-medium">{LIBELLE_ROLE[r.name] || r.name}</p>
                <p className="text-xs text-txt2 mt-0.5">
                  {r.permissions.length} permission{r.permissions.length > 1 ? "s" : ""}
                </p>
              </button>
            ))}
          </aside>

          {/* Matrice de permissions */}
          <section className="carte">
            <div className="flex items-center justify-between px-5 py-4 border-b border-bordure">
              <div>
                <h2 className="font-semibold text-sm">
                  Permissions — {LIBELLE_ROLE[selection?.name] || selection?.name}
                </h2>
                <p className="text-xs text-txt2 mt-0.5">
                  Cochez les actions autorisées pour ce rôle.
                </p>
              </div>
              <button onClick={enregistrer} disabled={!modifie || envoi} className="btn-primaire">
                {envoi ? "Enregistrement…" : "Enregistrer"}
              </button>
            </div>

            <div className="px-5 py-3 border-b border-bordure bg-accent/5">
              <p className="text-xs text-txt2 leading-snug">
                Les modifications prennent effet <strong className="text-txt">immédiatement</strong> pour tous
                les utilisateurs de ce rôle : les droits sont vérifiés en base à chaque requête, sans attendre
                l'expiration de leur session.
              </p>
            </div>

            <div className="divide-y divide-bordure">
              {permissions.map((p) => {
                const active = cochees.includes(p.code);
                // La ligne entière est le contrôle, et non un « label » posé
                // autour d'un bouton : un élément portant role="switch" n'est
                // plus étiquetable au sens HTML, si bien que l'association
                // n'existait pas. Ici l'interrupteur tire son nom accessible
                // de son propre contenu, la ligne reste cliquable de bout en
                // bout, et elle devient atteignable au clavier.
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => basculer(p.code)}
                    role="switch"
                    aria-checked={active}
                    className="w-full flex items-start gap-3 px-5 py-3.5 text-left cursor-pointer hover:bg-surface2/40 transition-colors"
                  >
                    <span
                      className={`w-10 h-[22px] rounded-full transition-colors relative shrink-0 mt-0.5 ${
                        active ? "bg-accent" : "bg-bordure"
                      }`}
                    >
                      <span
                        className={`absolute top-[3px] w-4 h-4 rounded-full bg-white transition-all ${
                          active ? "left-[22px]" : "left-[3px]"
                        }`}
                      />
                    </span>
                    <span className="block">
                      <span className="block text-sm font-medium">
                        {DESCRIPTIONS[p.code] || p.code}
                      </span>
                      <span className="block text-[11.5px] text-txt2 mt-0.5 font-mono">
                        {p.code}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </section>
        </div>
      )}
    </Layout>
  );
}
