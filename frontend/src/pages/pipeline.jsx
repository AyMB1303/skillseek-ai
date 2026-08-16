/**
 * Pipeline de recrutement : les candidatures en colonnes, déplaçables.
 *
 * La liste triée par note répond à « qui est le meilleur ? ». Elle ne répond
 * pas à « où en est chacun ? », qui est pourtant la question quotidienne d'un
 * recruteur. Les colonnes rendent visible d'un coup d'œil ce qui s'accumule :
 * dix dossiers reçus et jamais ouverts se voient, là où ils se noyaient dans
 * un tableau.
 *
 * Le glisser-déposer s'appuie sur l'API native du navigateur, sans
 * bibliothèque : le besoin est simple, et une dépendance de plus se paierait
 * à chaque mise à jour.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import Layout from "@/components/Layout";
import { useToast } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";
import { couleurScore } from "@/lib/scoring";

const COLONNES = [
  { statut: "received", libelle: "Reçues", teinte: "border-t-bordure" },
  { statut: "under_review", libelle: "En étude", teinte: "border-t-accent" },
  { statut: "shortlisted", libelle: "Présélectionnées", teinte: "border-t-cyan" },
  { statut: "interview", libelle: "Entretien", teinte: "border-t-alerte" },
  { statut: "hired", libelle: "Recrutées", teinte: "border-t-succes" },
];

export default function Pipeline() {
  const { chargement: garde } = useGarde(["recruiter"]);
  const { notifier } = useToast();
  const [candidatures, setCandidatures] = useState([]);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");
  const [survolee, setSurvolee] = useState(null);

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      const d = await api.candidatures();
      setCandidatures(d.applications);
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
    }
  }, []);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  const parColonne = useMemo(() => {
    const groupes = Object.fromEntries(COLONNES.map((c) => [c.statut, []]));
    candidatures.forEach((c) => {
      if (groupes[c.status]) groupes[c.status].push(c);
    });
    // Les mieux notés en tête de chaque colonne.
    Object.values(groupes).forEach((liste) =>
      liste.sort((a, b) => (b.score ?? -1) - (a.score ?? -1))
    );
    return groupes;
  }, [candidatures]);

  const deposer = async (statut, candidatureId) => {
    setSurvolee(null);
    const candidature = candidatures.find((c) => c.id === Number(candidatureId));
    if (!candidature || candidature.status === statut) return;

    const ancien = candidature.status;
    // Mise à jour optimiste : la carte se déplace à l'instant du lâcher, le
    // serveur confirme ensuite. Attendre l'aller-retour rendrait le geste mou.
    setCandidatures((l) =>
      l.map((c) => (c.id === candidature.id ? { ...c, status: statut } : c))
    );

    try {
      await api.changerStatut(candidature.id, statut);
      notifier(
        `${candidature.candidate?.full_name} → ${
          COLONNES.find((c) => c.statut === statut)?.libelle
        }`,
        {
          annuler: async () => {
            setCandidatures((l) =>
              l.map((c) => (c.id === candidature.id ? { ...c, status: ancien } : c))
            );
            await api.changerStatut(candidature.id, ancien).catch(() => {});
          },
        }
      );
    } catch (e) {
      setCandidatures((l) =>
        l.map((c) => (c.id === candidature.id ? { ...c, status: ancien } : c))
      );
      notifier(e.message, { type: "erreur" });
    }
  };

  if (garde) return null;

  return (
    <Layout titre="Pipeline" compteurCandidatures={candidatures.length}>
      <div className="space-y-4">
        <header>
          <h1 className="text-xl font-bold">Pipeline de recrutement</h1>
          <p className="text-[13px] text-txt2 mt-1">
            Faites glisser une carte d'une colonne à l'autre pour faire avancer
            la candidature. Les dossiers non retenus n'apparaissent pas ici.
          </p>
        </header>

        {etat === "chargement" && <p className="text-sm text-txt2">Chargement…</p>}
        {etat === "erreur" && <p className="text-sm text-erreur">{erreur}</p>}

        {etat === "ok" && (
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 items-start">
            {COLONNES.map((colonne) => (
              <section
                key={colonne.statut}
                onDragOver={(e) => {
                  e.preventDefault();
                  setSurvolee(colonne.statut);
                }}
                onDragLeave={() => setSurvolee((s) => (s === colonne.statut ? null : s))}
                onDrop={(e) => {
                  e.preventDefault();
                  deposer(colonne.statut, e.dataTransfer.getData("text/plain"));
                }}
                className={`rounded-xl2 border border-t-2 border-bordure ${colonne.teinte}
                            bg-surface2/40 p-2.5 min-h-[16rem] transition-colors ${
                              survolee === colonne.statut ? "bg-accent/8 border-accent/40" : ""
                            }`}
                aria-label={colonne.libelle}
              >
                <div className="flex items-baseline justify-between px-1 pb-2.5">
                  <h2 className="text-[12.5px] font-semibold">{colonne.libelle}</h2>
                  <span className="text-[11.5px] text-txt2">
                    {parColonne[colonne.statut].length}
                  </span>
                </div>

                <ul className="space-y-2">
                  {parColonne[colonne.statut].map((c) => (
                    <CarteCandidature key={c.id} candidature={c} />
                  ))}
                </ul>

                {parColonne[colonne.statut].length === 0 && (
                  <p className="text-[11.5px] text-txt2 text-center py-6 opacity-60">
                    Déposez une carte ici
                  </p>
                )}
              </section>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}

function CarteCandidature({ candidature: c }) {
  const coul = couleurScore(c.score);
  const signalee = (c.signalements || []).filter((s) => s.statut !== "ecarte").length > 0;

  return (
    <li
      draggable
      onDragStart={(e) => e.dataTransfer.setData("text/plain", String(c.id))}
      className="rounded-[10px] border border-bordure bg-surface p-2.5 cursor-grab
                 active:cursor-grabbing carte-reactive active:scale-[0.98]"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-[12.5px] font-medium leading-tight">
          {c.candidate?.full_name}
        </p>
        <span className={`text-[12px] font-bold shrink-0 ${coul.texte}`}>
          {c.score ?? "—"}
        </span>
      </div>
      <p className="text-[11px] text-txt2 mt-1 truncate">{c.offer?.title}</p>
      {signalee && (
        <span className="chip bg-alerte/15 text-alerte text-[10px] py-0 mt-1.5">
          à vérifier
        </span>
      )}
    </li>
  );
}
