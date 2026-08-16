/** Mes offres : liste, création réelle, ouverture/fermeture. */
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import SaisieCompetences from "@/components/SaisieCompetences";
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
  const [aSupprimer, setASupprimer] = useState(null);
  const [vivier, setVivier] = useState(null);

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
                      <td className="px-5 py-3 text-right whitespace-nowrap">
                        <Link href={`/candidatures?offre=${o.id}`} className="text-xs text-accent hover:text-cyan">
                          Candidatures
                        </Link>
                        <button
                          onClick={() => setVivier(o)}
                          className="text-xs text-cyan hover:text-accent ml-3"
                          title="Candidats déjà connus dont le profil correspond"
                        >
                          Vivier
                        </button>
                        <button
                          onClick={() => setASupprimer(o)}
                          className="text-xs text-txt2 hover:text-erreur ml-3"
                        >
                          Supprimer
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ))}

      <Modale
        ouverte={!!aSupprimer}
        onFermer={() => setASupprimer(null)}
        titre="Placer l'offre dans la corbeille"
        actions={
          <>
            <button onClick={() => setASupprimer(null)} className="btn-fantome">Annuler</button>
            <button
              onClick={async () => {
                try {
                  await api.supprimerOffre(aSupprimer.id);
                  setOffres((l) => l.filter((o) => o.id !== aSupprimer.id));
                  notifier("Offre placée dans la corbeille.");
                } catch (e) {
                  notifier(e.message, { type: "erreur" });
                } finally {
                  setASupprimer(null);
                }
              }}
              className="btn-primaire"
            >
              Placer dans la corbeille
            </button>
          </>
        }
      >
        <p className="text-sm">
          « <strong>{aSupprimer?.title}</strong> » ne sera plus visible par les candidats.
        </p>
        <p className="text-xs text-txt2 mt-2">
          L'offre et ses candidatures sont conservées : un administrateur peut la restaurer
          depuis la corbeille.
        </p>
      </Modale>

      <ModaleVivier offre={vivier} onFermer={() => setVivier(null)} />

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

/**
 * Vivier : candidats déjà connus dont le profil correspond à une offre.
 *
 * Une plateforme de recrutement accumule des profils analysés. Les laisser
 * dormir après une candidature revient à jeter l'essentiel de sa valeur :
 * quelqu'un ayant postulé au poste de backend il y a deux mois est peut-être
 * le profil recherché aujourd'hui, et personne ne pensera à l'aller chercher.
 */
function ModaleVivier({ offre, onFermer }) {
  const [donnees, setDonnees] = useState(null);
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    if (!offre) return;
    setChargement(true);
    setErreur("");
    setDonnees(null);
    api
      .vivier(offre.id)
      .then(setDonnees)
      .catch((e) => setErreur(e.message))
      .finally(() => setChargement(false));
  }, [offre]);

  return (
    <Modale
      ouverte={!!offre}
      onFermer={onFermer}
      titre={offre ? `Vivier — ${offre.title}` : ""}
      actions={<button onClick={onFermer} className="btn-secondaire">Fermer</button>}
    >
      {chargement && <p className="text-sm text-txt2">Rapprochement en cours…</p>}
      {erreur && <p className="text-sm text-erreur">{erreur}</p>}

      {donnees && (
        <div className="space-y-3">
          <p className="text-[12.5px] text-txt2 leading-snug">
            {donnees.profils.length === 0
              ? `Aucun profil connu n'atteint le seuil pour cette offre, sur ${donnees.examines} examinés.`
              : `${donnees.profils.length} profil(s) sur ${donnees.examines} examinés. Ces candidats n'ont pas postulé à cette offre.`}
          </p>

          <ul className="space-y-2 max-h-[24rem] overflow-y-auto">
            {donnees.profils.map((p) => (
              <li
                key={p.candidat_id}
                className="rounded-[10px] border border-bordure bg-surface2/50 p-3"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[13.5px] font-medium">{p.candidat}</span>
                  <span className="text-[13px] font-bold text-accent">{p.score}/100</span>
                </div>
                <p className="text-[11.5px] text-txt2 mt-0.5">{p.email}</p>
                {p.competences_trouvees.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {p.competences_trouvees.map((c) => (
                      <span key={c} className="chip bg-succes/15 text-succes text-[10.5px] py-0">
                        {c}
                      </span>
                    ))}
                  </div>
                )}
                <p className="text-[11px] text-txt2 mt-1.5 opacity-80">
                  Dernière candidature : {p.derniere_candidature.offre}
                </p>
              </li>
            ))}
          </ul>

          <p className="text-[11px] text-txt2 border-t border-bordure pt-2 leading-snug">
            {donnees.lecture}
          </p>
        </div>
      )}
    </Modale>
  );
}

function ModaleOffre({ ouverte, onFermer, onCree }) {
  const [f, setF] = useState({
    title: "", description: "", min_experience_years: 0, min_degree: "",
    location: "", contract_type: "", remote_policy: "", salary_min: "", salary_max: "",
  });
  const [competences, setCompetences] = useState([]);
  const [souhaitees, setSouhaitees] = useState([]);
  const [erreurs, setErreurs] = useState({});
  const [envoi, setEnvoi] = useState(false);
  const [suggerees, setSuggerees] = useState([]);

  // La détection tourne pendant que le recruteur écrit, avec un délai : le
  // relancer à chaque frappe saturerait le serveur sans rien apporter.
  useEffect(() => {
    if (f.description.trim().length < 30) {
      setSuggerees([]);
      return;
    }
    const minuteur = setTimeout(() => {
      api
        .detecterCompetences(f.description)
        .then((d) => setSuggerees(d.competences || []))
        .catch(() => setSuggerees([]));
    }, 700);
    return () => clearTimeout(minuteur);
  }, [f.description]);

  // Ne proposer que ce qui n'est pas déjà exigé ou souhaité.
  const detectees = suggerees.filter(
    (c) => !competences.includes(c) && !souhaitees.includes(c)
  );

  const soumettre = async (e) => {
    e.preventDefault();
    const err = {};
    if (f.title.trim().length < 3) err.title = "Intitulé requis (3 caractères minimum).";
    if (f.description.trim().length < 20) err.description = "Description trop courte (20 caractères minimum).";
    if (f.salary_min && f.salary_max && Number(f.salary_min) > Number(f.salary_max)) {
      err.salary = "Le salaire minimum ne peut dépasser le maximum.";
    }
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
      setF({
        title: "", description: "", min_experience_years: 0, min_degree: "",
        location: "", contract_type: "", remote_policy: "", salary_min: "", salary_max: "",
      });
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

          {/* Les compétences relevées dans la description sont, par
              construction, celles que le moteur saura retrouver dans un CV :
              les proposer supprime le risque d'exigence introuvable. */}
          {detectees.length > 0 && (
            <div className="mt-2 rounded-[10px] border border-cyan/30 bg-cyan/5 p-2.5">
              <p className="text-[11.5px] text-txt2 mb-1.5">
                Compétences repérées dans votre description — cliquez pour les exiger :
              </p>
              <div className="flex flex-wrap gap-1.5">
                {detectees.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setCompetences([...competences, c])}
                    className="chip bg-cyan/15 text-cyan hover:bg-cyan/25 text-[12px]"
                  >
                    + {c}
                  </button>
                ))}
                {detectees.length > 1 && (
                  <button
                    type="button"
                    onClick={() => setCompetences([...new Set([...competences, ...detectees])])}
                    className="text-[11.5px] text-accent hover:text-cyan px-1"
                  >
                    tout ajouter
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="lieu" className="etiquette">Localisation</label>
            <input id="lieu" className="champ" value={f.location}
              onChange={(e) => setF({ ...f, location: e.target.value })}
              placeholder="Casablanca, Rabat…" />
          </div>
          <div>
            <label htmlFor="contrat" className="etiquette">Type de contrat</label>
            <select id="contrat" className="champ" value={f.contract_type}
              onChange={(e) => setF({ ...f, contract_type: e.target.value })}>
              <option value="">Non précisé</option>
              {["CDI", "CDD", "Stage", "Alternance", "Freelance"].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label htmlFor="mode" className="etiquette">Mode de travail</label>
            <select id="mode" className="champ" value={f.remote_policy}
              onChange={(e) => setF({ ...f, remote_policy: e.target.value })}>
              <option value="">Non précisé</option>
              {["Sur site", "Hybride", "Télétravail"].map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="sal-min" className="etiquette">Salaire min. (MAD)</label>
            <input id="sal-min" type="number" min="0" step="500" className="champ"
              value={f.salary_min} onChange={(e) => setF({ ...f, salary_min: e.target.value })}
              placeholder="8000" />
          </div>
          <div>
            <label htmlFor="sal-max" className="etiquette">Salaire max. (MAD)</label>
            <input id="sal-max" type="number" min="0" step="500" className="champ"
              value={f.salary_max} onChange={(e) => setF({ ...f, salary_max: e.target.value })}
              placeholder="14000" />
          </div>
        </div>
        {erreurs.salary && <p className="text-xs text-erreur -mt-2">{erreurs.salary}</p>}

        <div>
          <label htmlFor="comp" className="etiquette">
            Compétences obligatoires <span className="font-normal">(Entrée ou virgule pour valider)</span>
          </label>
          <SaisieCompetences
            id="comp"
            valeurs={competences}
            onChange={setCompetences}
            placeholder="python, sql, docker… (Entrée pour valider)"
          />
          <p className="text-[11px] text-txt2 mt-1.5">
            Leur absence écarte automatiquement la candidature du classement.
          </p>
        </div>

        <div>
          <label htmlFor="comp-souhait" className="etiquette">
            Compétences souhaitées <span className="font-normal">(facultatif)</span>
          </label>
          <SaisieCompetences
            id="comp-souhait"
            valeurs={souhaitees}
            onChange={setSouhaitees}
            couleur="cyan"
            placeholder="power bi, kubernetes… (Entrée pour valider)"
          />
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
