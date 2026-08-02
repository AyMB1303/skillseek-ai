/** Recherche globale : filtre réellement offres et candidatures. */
import { useEffect, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import Layout from "@/components/Layout";
import { Chargement, EtatVide } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";
import { couleurScore } from "@/lib/scoring";

export default function Recherche() {
  const router = useRouter();
  const q = (router.query.q || "").toString().trim().toLowerCase();
  const { utilisateur, chargement: garde } = useGarde();
  const [donnees, setDonnees] = useState({ offres: [], candidatures: [] });
  const [pret, setPret] = useState(false);

  const charger = useCallback(async () => {
    try {
      const offres = await api.offres();
      let candidatures = { applications: [] };
      if (utilisateur?.role === "recruiter" || utilisateur?.role === "admin") {
        candidatures = await api.candidatures().catch(() => ({ applications: [] }));
      }
      setDonnees({ offres: offres.offers, candidatures: candidatures.applications });
    } finally {
      setPret(true);
    }
  }, [utilisateur]);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  const resultats = useMemo(() => {
    if (!q) return { offres: [], candidats: [] };
    return {
      offres: donnees.offres.filter(
        (o) =>
          o.title.toLowerCase().includes(q) ||
          (o.required_skills || []).some((s) => s.includes(q))
      ),
      candidats: donnees.candidatures.filter(
        (c) =>
          (c.candidate?.full_name || "").toLowerCase().includes(q) ||
          (c.candidate?.email || "").toLowerCase().includes(q)
      ),
    };
  }, [q, donnees]);

  if (garde) return null;

  const total = resultats.offres.length + resultats.candidats.length;

  return (
    <Layout titre="Recherche">
      <p className="text-sm text-txt2 mb-5">
        {q ? `${total} résultat(s) pour « ${q} »` : "Saisissez un terme dans la barre de recherche."}
      </p>

      {!pret && q && <Chargement lignes={2} />}

      {pret && q && total === 0 && (
        <EtatVide titre="Aucun résultat" description="Essayez un autre terme ou vérifiez l'orthographe." />
      )}

      {resultats.offres.length > 0 && (
        <section className="mb-6">
          <h2 className="text-xs font-semibold text-txt2 uppercase tracking-wide mb-2.5">
            Offres ({resultats.offres.length})
          </h2>
          <div className="carte divide-y divide-bordure">
            {resultats.offres.map((o) => (
              <Link key={o.id} href={`/offres/${o.id}`} className="block px-5 py-3.5 hover:bg-surface2/60">
                <p className="font-medium text-sm">{o.title}</p>
                <p className="text-xs text-txt2 mt-0.5">{(o.required_skills || []).join(" · ")}</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      {resultats.candidats.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold text-txt2 uppercase tracking-wide mb-2.5">
            Candidats ({resultats.candidats.length})
          </h2>
          <div className="carte divide-y divide-bordure">
            {resultats.candidats.map((c) => {
              const coul = couleurScore(c.score);
              return (
                <Link
                  key={c.id}
                  href={`/candidatures?id=${c.id}`}
                  className="flex items-center justify-between px-5 py-3.5 hover:bg-surface2/60"
                >
                  <div>
                    <p className="font-medium text-sm">{c.candidate?.full_name}</p>
                    <p className="text-xs text-txt2 mt-0.5">{c.offer?.title}</p>
                  </div>
                  <span className={`chip ${coul.fond} ${coul.texte} font-semibold`}>
                    {c.score ?? "—"}{c.score != null && "/100"}
                  </span>
                </Link>
              );
            })}
          </div>
        </section>
      )}
    </Layout>
  );
}
