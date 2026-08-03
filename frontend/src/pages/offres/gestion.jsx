/** Mes offres : liste, création réelle, ouverture/fermeture. */
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur, EtatVide, Modale, useToast } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";

export default function GestionOffres() {
  const { chargement: garde } = useGarde(["recruiter"]);
  const { notifier } = useToast();
  const [offres, setOffres] = useState([]);
  const [candidatures, setCandidatures] = useState([]);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");
  const [modale, setModale] = useState(false);

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      const [o, c] = await Promise.all([api.offres(), api.candidatures()]);
      setOffres(o.offers);
      setCandidatures(c.applications);
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
    }
  }, []);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  const stats = (offreId) => {
    const liste = candidatures.filter((c) => c.offer?.id === offreId);
    const scores = liste.map((c) => c.score).filter((s) => s != null);
    return {
      nb: liste.length,
      moyenne: scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null,
    };
  };

  const basculerStatut = async (offre) => {
    const nouveau = offre.status === "open" ? "closed" : "open";
    setOffres((l) => l.map((o) => (o.id === offre.id ? { ...o, status: nouveau } : o)));
    try {
      await api.modifierOffre(offre.id, { status: nouveau });
      notifier(nouveau === "open" ? "Offre rouverte." : "Offre fermée.");
    } catch (e) {
      setOffres((l) => l.map((o) => (o.id === offre.id ? { ...o, status: offre.status } : o)));
      notifier(e.message, { type: "erreur" });
    }
  };

  if (garde) return null;

  return (
    <Layout titre="Mes offres" compteurCandidatures={candidatures.length}>
      <div className="flex justify-end mb-5">
        <button onClick={() => setModale(true)} className="btn-primaire">+ Nouvelle offre</button>
      </div>

      {etat === "chargement" && <Chargement lignes={4} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" &&
        (offres.length === 0 ? (
          <EtatVide
            titre="Aucune offre publiée"
            description="Créez votre première offre pour commencer à recevoir des candidatures."
            action={<button onClick={() => setModale(true)} className="btn-primaire mt-2">Créer une offre</button>}
          />
        ) : (
          <div className="carte overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-txt2 text-xs border-b border-bordure">
                  <th className="px-5 py-3 font-medium">Intitulé</th>
                  <th className="px-5 py-3 font-medium">Candidatures</th>
                  <th className="px-5 py-3 font-medium">Score moyen</th>
                  <th className="px-5 py-3 font-medium">Statut</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody>
                {offres.map((o) => {
                  const s = stats(o.id);
                  return (
                    <tr key={o.id} className="border-b border-bordure last:border-0 hover:bg-surface2/60">
                      <td className="px-5 py-3">
                        <div className="font-medium">{o.title}</div>
                        <div className="text-xs text-txt2">
                          {(o.required_skills || []).slice(0, 3).join(" · ") || "Aucune compétence précisée"}
                        </div>
                      </td>
                      <td className="px-5 py-3">{s.nb}</td>
                      <td className="px-5 py-3 text-txt2">{s.moyenne != null ? `${s.moyenne}/100` : "—"}</td>
                      <td className="px-5 py-3">
                        <button
                          onClick={() => basculerStatut(o)}
                          className={`chip ${o.status === "open" ? "bg-succes/15 text-succes" : "bg-bordure/50 text-txt2"}`}
                        >
                          {o.status === "open" ? "Ouverte" : "Fermée"}
                        </button>
                      </td>
                      <td className="px-5 py-3 text-right">
                        <Link href={`/candidatures?offre=${o.id}`} className="text-xs text-accent hover:text-cyan">
                          Voir les candidatures
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ))}

      <ModaleOffre
        ouverte={modale}
        onFermer={() => setModale(false)}
        onCree={(offre) => {
          setOffres((l) => [offre, ...l]);
          notifier("Offre publiée. Elle est visible par les candidats.");
          setModale(false);
        }}
      />
    </Layout>
  );
}

function ModaleOffre({ ouverte, onFermer, onCree }) {
  const [f, setF] = useState({ title: "", description: "", min_experience_years: 0, min_degree: "" });
  const [competences, setCompetences] = useState([]);
  const [souhaitees, setSouhaitees] = useState([]);
  const [saisie, setSaisie] = useState("");
  const [saisieSouhaitee, setSaisieSouhaitee] = useState("");
  const [erreurs, setErreurs] = useState({});
  const [envoi, setEnvoi] = useState(false);

  const ajouter = (e) => {
    if (e.key !== "Enter" || !saisie.trim()) return;
    e.preventDefault();
    const v = saisie.trim().toLowerCase();
    if (!competences.includes(v)) setCompetences([...competences, v]);
    setSaisie("");
  };

  const ajouterSouhaitee = (e) => {
    if (e.key !== "Enter" || !saisieSouhaitee.trim()) return;
    e.preventDefault();
    const v = saisieSouhaitee.trim().toLowerCase();
    if (!souhaitees.includes(v)) setSouhaitees([...souhaitees, v]);
    setSaisieSouhaitee("");
  };

  const soumettre = async (e) => {
    e.preventDefault();
    const err = {};
    if (f.title.trim().length < 3) err.title = "Intitulé requis (3 caractères minimum).";
    if (f.description.trim().length < 20) err.description = "Description trop courte (20 caractères minimum).";
    setErreurs(err);
    if (Object.keys(err).length) return;

    setEnvoi(true);
    try {
      const d = await api.creerOffre({
        ...f,
        required_skills: competences,
        preferred_skills: souhaitees,
      });
      onCree(d.offer);
      setF({ title: "", description: "", min_experience_years: 0, min_degree: "" });
      setCompetences([]);
      setSouhaitees([]);
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
      titre="Nouvelle offre d'emploi"
      actions={
        <>
          <button onClick={onFermer} className="btn-fantome">Annuler</button>
          <button onClick={soumettre} disabled={envoi} className="btn-primaire">
            {envoi ? "Publication…" : "Publier l'offre"}
          </button>
        </>
      }
    >
      <form onSubmit={soumettre} className="space-y-4" noValidate>
        {erreurs.general && <p className="text-sm text-erreur">{erreurs.general}</p>}

        <div>
          <label htmlFor="titre" className="etiquette">Intitulé du poste</label>
          <input id="titre" className={`champ ${erreurs.title ? "border-erreur" : ""}`}
            value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })}
            placeholder="Développeur Python Senior" />
          {erreurs.title && <p className="text-xs text-erreur mt-1.5">{erreurs.title}</p>}
        </div>

        <div>
          <label htmlFor="desc" className="etiquette">Description</label>
          <textarea id="desc" rows={4} className={`champ resize-none ${erreurs.description ? "border-erreur" : ""}`}
            value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })}
            placeholder="Missions, contexte de l'équipe, environnement technique…" />
          {erreurs.description && <p className="text-xs text-erreur mt-1.5">{erreurs.description}</p>}
        </div>

        <div>
          <label htmlFor="comp" className="etiquette">
            Compétences obligatoires <span className="font-normal">(Entrée pour ajouter)</span>
          </label>
          <input id="comp" className="champ" value={saisie} onChange={(e) => setSaisie(e.target.value)}
            onKeyDown={ajouter} placeholder="python, sql, docker…" />
          {competences.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {competences.map((c) => (
                <button key={c} type="button" onClick={() => setCompetences(competences.filter((x) => x !== c))}
                  className="chip bg-accent/15 text-accent hover:bg-erreur/15 hover:text-erreur">
                  {c} ×
                </button>
              ))}
            </div>
          )}
          <p className="text-[11px] text-txt2 mt-1.5">
            Leur absence écarte automatiquement la candidature du classement.
          </p>
        </div>

        <div>
          <label htmlFor="comp-souhait" className="etiquette">
            Compétences souhaitées <span className="font-normal">(facultatif)</span>
          </label>
          <input id="comp-souhait" className="champ" value={saisieSouhaitee}
            onChange={(e) => setSaisieSouhaitee(e.target.value)}
            onKeyDown={ajouterSouhaitee} placeholder="power bi, kubernetes…" />
          {souhaitees.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {souhaitees.map((c) => (
                <button key={c} type="button" onClick={() => setSouhaitees(souhaitees.filter((x) => x !== c))}
                  className="chip bg-cyan/15 text-cyan hover:bg-erreur/15 hover:text-erreur">
                  {c} ×
                </button>
              ))}
            </div>
          )}
          <p className="text-[11px] text-txt2 mt-1.5">
            Elles valorisent le profil sans être bloquantes.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="exp" className="etiquette">Expérience minimale (années)</label>
            <input id="exp" type="number" min="0" max="20" className="champ"
              value={f.min_experience_years}
              onChange={(e) => setF({ ...f, min_experience_years: Number(e.target.value) })} />
          </div>
          <div>
            <label htmlFor="dip" className="etiquette">Diplôme minimal</label>
            <select id="dip" className="champ" value={f.min_degree}
              onChange={(e) => setF({ ...f, min_degree: e.target.value })}>
              <option value="">Non exigé</option>
              <option value="Bac">Bac</option>
              <option value="Bac+2">Bac+2</option>
              <option value="Bac+3">Bac+3</option>
              <option value="Bac+5">Bac+5</option>
            </select>
          </div>
        </div>

        <p className="text-[11px] text-txt2 leading-snug">
          Ces deux critères sont éliminatoires : tout candidat ne les remplissant pas sera écarté du classement,
          avec le motif indiqué au recruteur.
        </p>
      </form>
    </Modale>
  );
}
