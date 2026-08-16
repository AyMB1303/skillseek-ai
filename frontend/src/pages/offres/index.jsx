/** Liste des offres ouvertes, avec recherche et filtre par compétence. */
import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur, EtatVide } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";
import { retard } from "@/lib/mouvement";

export default function Offres() {
  const { chargement: garde } = useGarde(["candidate", "recruiter", "admin"]);
  const [offres, setOffres] = useState([]);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");
  const [recherche, setRecherche] = useState("");
  const [competence, setCompetence] = useState("");

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      const d = await api.offres();
      setOffres(d.offers);
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
    }
  }, []);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  const competences = useMemo(
    () => [...new Set(offres.flatMap((o) => o.required_skills || []))].sort(),
    [offres]
  );

  const filtrees = useMemo(() => {
    const q = recherche.trim().toLowerCase();
    return offres.filter((o) => {
      const correspond = !q || o.title.toLowerCase().includes(q) || o.description.toLowerCase().includes(q);
      const aCompetence = !competence || (o.required_skills || []).includes(competence);
      return correspond && aCompetence;
    });
  }, [offres, recherche, competence]);

  if (garde) return null;

  return (
    <Layout titre="Offres d'emploi">
      <div className="flex flex-wrap gap-3 mb-5">
        <input
          type="search"
          className="champ max-w-sm"
          placeholder="Rechercher un poste…"
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          aria-label="Rechercher une offre"
        />
        {/* Le filtre n'a de sens que si des compétences sont déclarées sur les offres */}
        {competences.length > 0 && (
          <select
            className="champ max-w-[220px]"
            value={competence}
            onChange={(e) => setCompetence(e.target.value)}
            aria-label="Filtrer par compétence"
          >
            <option value="">Toutes les compétences</option>
            {competences.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        )}
        {(recherche || competence) && (
          <button
            onClick={() => { setRecherche(""); setCompetence(""); }}
            className="btn-fantome"
          >
            Réinitialiser
          </button>
        )}
        <span className="ml-auto self-center text-sm text-txt2">
          {filtrees.length} offre{filtrees.length > 1 ? "s" : ""}
        </span>
      </div>

      {etat === "chargement" && <Chargement lignes={3} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" &&
        (filtrees.length === 0 ? (
          <EtatVide
            titre={offres.length ? "Aucun résultat" : "Aucune offre disponible"}
            description={
              offres.length
                ? "Essayez d'élargir votre recherche."
                : "Revenez bientôt : de nouvelles offres sont publiées régulièrement."
            }
            action={
              offres.length ? (
                <button onClick={() => { setRecherche(""); setCompetence(""); }} className="btn-secondaire mt-2">
                  Réinitialiser les filtres
                </button>
              ) : null
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filtrees.map((o, rang) => (
              <Link
                key={o.id}
                href={`/offres/${o.id}`}
                className="carte carte-reactive p-5 flex flex-col gap-3 entree"
                style={{ animationDelay: retard(rang, 45) }}
              >
                <div>
                  <h2 className="font-semibold leading-snug">{o.title}</h2>
                  <p className="text-[13px] text-txt2 mt-1.5 line-clamp-2">{o.description}</p>
                </div>

                <div className="flex flex-wrap gap-1.5">
                  {(o.required_skills || []).slice(0, 4).map((s) => (
                    <span key={s} className="chip bg-accent/10 text-accent">{s}</span>
                  ))}
                </div>

                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-auto pt-2 text-xs text-txt2 border-t border-bordure">
                  {o.location && <span>{o.location}</span>}
                  {o.contract_type && (
                    <span className="chip bg-bordure/40 text-txt2 text-[10px]">{o.contract_type}</span>
                  )}
                  {o.remote_policy && <span>{o.remote_policy}</span>}
                  {o.min_experience_years > 0 && <span>{o.min_experience_years}+ ans</span>}
                  <span className="ml-auto">{new Date(o.created_at).toLocaleDateString("fr-FR")}</span>
                </div>

                {o.salary_display && (
                  <p className="text-xs font-medium text-succes">{o.salary_display}</p>
                )}
              </Link>
            ))}
          </div>
        ))}
    </Layout>
  );
}
