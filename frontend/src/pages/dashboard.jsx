/** Dashboard recruteur : KPI, entonnoir et courbe calculés depuis l'API. */
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur, EtatVide, BadgeStatut } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";
import { couleurScore } from "@/lib/scoring";

const PERIODES = [
  { valeur: 7, libelle: "7 jours" },
  { valeur: 30, libelle: "30 jours" },
  { valeur: 90, libelle: "90 jours" },
];

export default function Dashboard() {
  const { chargement: garde } = useGarde(["recruiter"]);
  const [periode, setPeriode] = useState(30);
  const [stats, setStats] = useState(null);
  const [dernieres, setDernieres] = useState([]);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      const [s, c] = await Promise.all([api.statistiques(periode), api.candidatures()]);
      setStats(s);
      setDernieres(c.applications.slice(0, 8));
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
    }
  }, [periode]);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  if (garde) return null;

  return (
    <Layout titre="Tableau de bord" compteurCandidatures={stats?.kpi.recues.valeur}>
      {/* Sélecteur de période : recalcule réellement les données */}
      <div className="flex items-center justify-between mb-5">
        <p className="text-sm text-txt2">
          {stats ? `${stats.offres_ouvertes} offre(s) ouverte(s)` : " "}
        </p>
        <div className="flex gap-1 bg-surface border border-bordure rounded-[10px] p-1">
          {PERIODES.map((p) => (
            <button
              key={p.valeur}
              onClick={() => setPeriode(p.valeur)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                periode === p.valeur ? "bg-accent text-white" : "text-txt2 hover:text-txt"
              }`}
              aria-pressed={periode === p.valeur}
            >
              {p.libelle}
            </button>
          ))}
        </div>
      </div>

      {etat === "chargement" && <Chargement lignes={4} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" && stats && (
        <div className="space-y-5">
          {/* ---------- Cartes KPI ---------- */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <CarteKpi libelle="Candidatures reçues" valeur={stats.kpi.recues.valeur} variation={stats.kpi.recues.variation} />
            <CarteKpi libelle="Présélectionnés IA" valeur={stats.kpi.preselectionnees.valeur} accent="cyan" />
            <CarteKpi libelle="Entretiens" valeur={stats.kpi.entretiens.valeur} accent="alerte" />
            <CarteKpi libelle="Recrutés" valeur={stats.kpi.recrutes.valeur} accent="succes" />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <Entonnoir etapes={stats.funnel} />
            <Courbe serie={stats.serie} periode={periode} />
          </div>

          {/* ---------- Dernières candidatures ---------- */}
          <section className="carte overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-bordure">
              <h2 className="font-semibold text-sm">Dernières candidatures</h2>
              <Link href="/candidatures" className="text-xs text-accent hover:text-cyan">Tout voir</Link>
            </div>
            {dernieres.length === 0 ? (
              <EtatVide titre="Aucune candidature" description="Les candidatures apparaîtront ici dès réception." />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-txt2 text-xs border-b border-bordure">
                    <th className="px-5 py-2.5 font-medium">Candidat</th>
                    <th className="px-5 py-2.5 font-medium">Offre</th>
                    <th className="px-5 py-2.5 font-medium">Score</th>
                    <th className="px-5 py-2.5 font-medium">Statut</th>
                    <th className="px-5 py-2.5" />
                  </tr>
                </thead>
                <tbody>
                  {dernieres.map((c) => {
                    const coul = couleurScore(c.score);
                    return (
                      <tr key={c.id} className="border-b border-bordure last:border-0 hover:bg-surface2/60">
                        <td className="px-5 py-3 font-medium">{c.candidate?.full_name}</td>
                        <td className="px-5 py-3 text-txt2">{c.offer?.title}</td>
                        <td className="px-5 py-3">
                          <span className={`chip ${coul.fond} ${coul.texte} font-semibold`}>
                            {c.score ?? "—"}{c.score != null && "/100"}
                          </span>
                        </td>
                        <td className="px-5 py-3"><BadgeStatut statut={c.status} /></td>
                        <td className="px-5 py-3 text-right">
                          <Link href={`/candidatures?id=${c.id}`} className="text-xs text-accent hover:text-cyan">
                            Voir
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </section>
        </div>
      )}
    </Layout>
  );
}

/* ---------------------------- Sous-composants ---------------------------- */

function CarteKpi({ libelle, valeur, variation, accent = "accent" }) {
  const couleurs = { accent: "text-accent", cyan: "text-cyan", alerte: "text-alerte", succes: "text-succes" };
  return (
    <div className="carte p-4">
      <p className="text-xs text-txt2 font-medium">{libelle}</p>
      <div className="flex items-end gap-2 mt-2">
        <span className={`text-3xl font-bold ${couleurs[accent]}`}>{valeur}</span>
        {variation != null && (
          <span className={`text-xs font-semibold mb-1.5 ${variation >= 0 ? "text-succes" : "text-erreur"}`}>
            {variation >= 0 ? "▲" : "▼"} {Math.abs(variation)}%
          </span>
        )}
      </div>
    </div>
  );
}

function Entonnoir({ etapes }) {
  const max = Math.max(...etapes.map((e) => e.valeur), 1);
  const couleurs = ["bg-accent", "bg-cyan", "bg-alerte", "bg-succes"];
  return (
    <section className="carte p-5">
      <h2 className="font-semibold text-sm mb-4">Entonnoir de recrutement</h2>
      <div className="space-y-2.5">
        {etapes.map((e, i) => (
          <div key={e.etape}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-txt2">{e.etape}</span>
              <span className="font-semibold">
                {e.valeur}
                {i > 0 && <span className="text-txt2 font-normal ml-1.5">({e.taux}%)</span>}
              </span>
            </div>
            <div className="h-7 bg-fond rounded-md overflow-hidden">
              <div
                className={`h-full ${couleurs[i]} transition-all duration-500 rounded-md`}
                style={{ width: `${Math.max((e.valeur / max) * 100, e.valeur ? 4 : 0)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Courbe({ serie, periode }) {
  if (!serie.length) {
    return (
      <section className="carte p-5">
        <h2 className="font-semibold text-sm mb-4">Candidatures sur {periode} jours</h2>
        <p className="text-sm text-txt2 py-10 text-center">Aucune donnée sur la période.</p>
      </section>
    );
  }
  const max = Math.max(...serie.map((p) => p.valeur), 1);
  const pas = serie.length > 1 ? 100 / (serie.length - 1) : 0;
  const points = serie.map((p, i) => `${i * pas},${40 - (p.valeur / max) * 36}`).join(" ");

  return (
    <section className="carte p-5">
      <h2 className="font-semibold text-sm mb-4">Candidatures sur {periode} jours</h2>
      <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="w-full h-32" role="img" aria-label="Évolution des candidatures">
        <polyline points={points} fill="none" stroke="#3B82F6" strokeWidth="1" vectorEffect="non-scaling-stroke" />
        <polygon points={`0,40 ${points} 100,40`} fill="url(#deg)" opacity="0.25" />
        <defs>
          <linearGradient id="deg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3B82F6" />
            <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
      <div className="flex justify-between text-[11px] text-txt2 mt-1">
        <span>{serie[0].jour}</span>
        <span>{serie[serie.length - 1].jour}</span>
      </div>
    </section>
  );
}
