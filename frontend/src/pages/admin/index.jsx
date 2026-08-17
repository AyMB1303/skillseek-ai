/** Tableau de bord administrateur : vue d'ensemble de la plateforme. */
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";
import { useCompteur, useEntreeEnVue, retard } from "@/lib/mouvement";

const LIBELLE_ROLE = { admin: "Administrateurs", recruiter: "Recruteurs", candidate: "Candidats" };

export default function TableauDeBordAdmin() {
  const { chargement: garde } = useGarde(["admin"]);
  const [stats, setStats] = useState(null);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      setStats(await api.statistiquesAdmin());
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
    }
  }, []);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  if (garde) return null;

  return (
    <Layout titre="Tableau de bord">
      {etat === "chargement" && <Chargement lignes={4} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" && stats && (
        <div className="space-y-5">
          {/* Demandes en attente : action prioritaire */}
          {stats.comptes.en_attente > 0 && (
            <Link
              href="/admin/recruteurs"
              className="carte flex items-center gap-4 p-4 border-alerte/40 bg-alerte/5 hover:border-alerte transition-colors"
            >
              <span className="w-10 h-10 rounded-full bg-alerte/15 text-alerte grid place-items-center text-lg shrink-0">
                ⏳
              </span>
              <div className="flex-1">
                <p className="font-semibold text-sm">
                  {stats.comptes.en_attente} demande(s) de compte recruteur en attente
                </p>
                <p className="text-xs text-txt2 mt-0.5">
                  Ces comptes ne peuvent pas se connecter tant qu'ils ne sont pas validés.
                </p>
              </div>
              <span className="text-accent text-sm">Traiter →</span>
            </Link>
          )}

          {/* Indicateurs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <Carte libelle="Comptes actifs" valeur={stats.comptes.total} accent="accent" rang={0} />
            <Carte libelle="Offres publiées" valeur={stats.offres.total} detail={`${stats.offres.ouvertes} ouverte(s)`} accent="cyan" rang={1} />
            <Carte libelle="Candidatures reçues" valeur={stats.candidatures.total} accent="succes" rang={2} />
            <Carte
              libelle="Éléments en corbeille"
              valeur={stats.corbeille.total}
              lien="/admin/corbeille"
              accent="alerte"
              rang={3}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Répartition par rôle */}
            <section className="carte p-5">
              <h2 className="font-semibold text-sm mb-4">Répartition des comptes</h2>
              <div className="space-y-3">
                {Object.entries(stats.comptes.par_role).map(([role, nombre], rang) => {
                  const part = stats.comptes.total ? (nombre / stats.comptes.total) * 100 : 0;
                  return (
                    <div key={role} className="entree" style={{ animationDelay: retard(rang, 80) }}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-txt2">{LIBELLE_ROLE[role] || role}</span>
                        <span className="font-semibold">{nombre}</span>
                      </div>
                      <div className="h-2 bg-fond rounded-full overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full jauge-remplissage"
                          style={{ width: `${part}%`, animationDelay: retard(rang, 80) }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {stats.comptes.desactives > 0 && (
                <p className="text-xs text-txt2 mt-4 pt-3 border-t border-bordure">
                  {stats.comptes.desactives} compte(s) désactivé(s).
                </p>
              )}
            </section>

            {/* Derniers comptes créés */}
            <section className="carte overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-bordure">
                <h2 className="font-semibold text-sm">Derniers comptes créés</h2>
                <Link href="/admin/utilisateurs" className="text-xs text-accent hover:text-cyan">
                  Tout voir
                </Link>
              </div>
              <div className="divide-y divide-bordure">
                {stats.derniers_comptes.map((u, rang) => (
                  <div
                    key={u.id}
                    className="flex items-center gap-3 px-5 py-3 entree hover:bg-surface2/50 transition-colors"
                    style={{ animationDelay: retard(rang, 55) }}
                  >
                    <div className="w-8 h-8 rounded-full bg-bordure text-cyan grid place-items-center text-[11px] font-bold shrink-0">
                      {u.full_name.split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-[13px] font-medium truncate">{u.full_name}</p>
                      <p className="text-[11px] text-txt2 truncate">{u.email}</p>
                    </div>
                    <span className="chip bg-bordure/40 text-txt2 text-[10px] shrink-0">
                      {LIBELLE_ROLE[u.role]?.slice(0, -1) || u.role}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}
    </Layout>
  );
}

function Carte({ libelle, valeur, detail, lien, accent = "accent", rang = 0 }) {
  const couleurs = { accent: "text-accent", cyan: "text-cyan", succes: "text-succes", alerte: "text-alerte" };
  const affiche = useCompteur(valeur ?? 0, { duree: 800 });
  const contenu = (
    <>
      <p className="text-xs text-txt2 font-medium">{libelle}</p>
      <p
        className={`text-3xl font-bold mt-2 tabular-nums ${couleurs[accent]}`}
        aria-label={`${libelle} : ${valeur}`}
      >
        {affiche}
      </p>
      {detail && <p className="text-[11px] text-txt2 mt-1">{detail}</p>}
    </>
  );

  const style = { animationDelay: retard(rang, 70) };
  return lien ? (
    <Link href={lien} className="carte carte-reactive p-4 entree" style={style}>{contenu}</Link>
  ) : (
    <div className="carte carte-reactive p-4 entree" style={style}>{contenu}</div>
  );
}
