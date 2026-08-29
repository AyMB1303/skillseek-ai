/**
 * Profil professionnel du candidat, et offres qui en découlent.
 *
 * Une plateforme de recrutement qui laisse le candidat parcourir seul un
 * catalogue de vingt offres ne lui rend pas service : il postule au jugé, et
 * le recruteur reçoit des dossiers hors sujet. Les deux y perdent.
 *
 * Cet écran retourne le moteur. Le même calcul qui répond « ce candidat
 * convient-il à cette offre ? » répond ici « quelles offres conviennent à ce
 * profil ? » — sans rien réimplémenter.
 *
 * **Aucune note n'est affichée, et c'est une règle, pas un oubli.** Un chiffre
 * sans son barème invite au malentendu, et quelqu'un qui aurait lu « 87 % »
 * avant d'être écarté aurait un grief légitime. Ce qui est montré, ce sont les
 * faits : les compétences reconnues, et surtout celles qui manquent — la seule
 * chose que le candidat puisse corriger.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import SaisieCompetences from "@/components/SaisieCompetences";
import { Chargement, EtatVide, useToast } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";
import { retard } from "@/lib/mouvement";

const DIPLOMES = ["", "bac", "bac+2", "bac+3", "bac+5", "doctorat"];
const CONTRATS = ["", "CDI", "CDD", "Stage", "Alternance", "Freelance"];

const CORRESPONDANCE = {
  forte: {
    libelle: "Toutes les compétences demandées",
    style: "bg-succes/12 text-succes border-succes/35",
  },
  partielle: {
    libelle: "La plupart des compétences",
    style: "bg-alerte/12 text-alerte border-alerte/35",
  },
  eloignee: {
    libelle: "Quelques compétences",
    style: "bg-bordure/50 text-txt2 border-bordure",
  },
  ouverte: {
    libelle: "Aucune compétence exigée",
    style: "bg-accent/10 text-accent border-accent/30",
  },
};

export default function MonProfilPro() {
  const { chargement: garde } = useGarde(["candidate"]);
  const { notifier } = useToast();

  const [profil, setProfil] = useState({
    skills: [], experience_years: 0, degree: "", ville: "", contrat: "",
  });
  const [origine, setOrigine] = useState(null);
  const [recommandations, setRecommandations] = useState(null);
  const [chargement, setChargement] = useState(true);
  const [envoi, setEnvoi] = useState(false);

  const chargerRecommandations = useCallback(async () => {
    try {
      setRecommandations(await api.recommandations());
    } catch {
      /* l'écran reste utilisable sans : le formulaire est l'essentiel */
    }
  }, []);

  useEffect(() => {
    if (garde) return;
    let actif = true;
    api
      .profilCompetences()
      .then((d) => {
        if (!actif) return;
        if (d.declare) setProfil({ ...profil, ...d.declare });
        setOrigine(d.origine);
      })
      .catch(() => {})
      .finally(() => actif && setChargement(false));
    chargerRecommandations();
    return () => { actif = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [garde, chargerRecommandations]);

  const enregistrer = async (e) => {
    e.preventDefault();
    setEnvoi(true);
    try {
      await api.enregistrerCompetences(profil);
      notifier("Profil enregistré. Vos suggestions sont à jour.");
      await chargerRecommandations();
    } catch (err) {
      notifier(err.details?.skills || err.message, { type: "erreur" });
    } finally {
      setEnvoi(false);
    }
  };

  if (garde) return null;

  return (
    <Layout titre="Mon profil professionnel">
      <div className="max-w-4xl space-y-5">

        <p className="text-[13px] text-txt2 max-w-2xl leading-relaxed">
          Indiquez ce que vous savez faire : la plateforme vous proposera les
          offres dont vous êtes le plus proche, et vous dira ce qu'il vous
          manque pour les autres. Rien n'est obligatoire, et ces informations
          ne sont pas transmises aux recruteurs — elles servent uniquement à
          vous orienter.
        </p>

        {chargement ? (
          <Chargement lignes={3} />
        ) : (
          <>
            {origine === "cv" && (
              <p className="rounded-[10px] border border-accent/30 bg-accent/8 p-3 text-[12.5px] leading-relaxed">
                Vos suggestions s'appuient désormais sur le <strong>profil
                extrait de votre CV</strong>, plus fiable qu'une déclaration.
                Ce formulaire reste modifiable, mais il ne sert plus au
                classement.
              </p>
            )}

            <form onSubmit={enregistrer} className="carte p-6 space-y-5 entree">
              <div>
                {/* L'étiquette désigne explicitement le champ de saisie que
                    SaisieCompetences rend sous cet identifiant. Sans « for »,
                    elle n'était qu'un texte : un lecteur d'écran annonçait un
                    champ sans nom. */}
                <label className="etiquette" htmlFor="competences-profil">
                  Vos compétences
                </label>
                <SaisieCompetences
                  id="competences-profil"
                  valeurs={profil.skills}
                  onChange={(skills) => setProfil({ ...profil, skills })}
                  placeholder="python, sql, gestion de projet…"
                />
                <p className="text-[11px] text-txt2 mt-1.5">
                  Saisissez-en autant que vous voulez. Les suggestions viennent
                  du référentiel utilisé pour lire les offres : une compétence
                  reconnue sera retrouvée à coup sûr.
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="exp" className="etiquette">Années d'expérience</label>
                  <input
                    id="exp" type="number" min="0" max="60" className="champ"
                    value={profil.experience_years}
                    onChange={(e) =>
                      setProfil({ ...profil, experience_years: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label htmlFor="dip" className="etiquette">Niveau de diplôme</label>
                  <select
                    id="dip" className="champ" value={profil.degree || ""}
                    onChange={(e) => setProfil({ ...profil, degree: e.target.value })}
                  >
                    {DIPLOMES.map((d) => (
                      <option key={d} value={d}>{d || "Non renseigné"}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label htmlFor="ville" className="etiquette">
                    Ville souhaitée <span className="font-normal">(facultatif)</span>
                  </label>
                  <input
                    id="ville" className="champ" value={profil.ville || ""}
                    placeholder="Casablanca"
                    onChange={(e) => setProfil({ ...profil, ville: e.target.value })}
                  />
                </div>
                <div>
                  <label htmlFor="contrat" className="etiquette">
                    Type de contrat <span className="font-normal">(facultatif)</span>
                  </label>
                  <select
                    id="contrat" className="champ" value={profil.contrat || ""}
                    onChange={(e) => setProfil({ ...profil, contrat: e.target.value })}
                  >
                    {CONTRATS.map((c) => (
                      <option key={c} value={c}>{c || "Peu importe"}</option>
                    ))}
                  </select>
                </div>
              </div>
              <p className="text-[11px] text-txt2 -mt-2">
                La ville et le contrat écartent les offres qui ne vous
                conviennent pas ; aucune correspondance de compétences ne les
                compense.
              </p>

              <button type="submit" disabled={envoi} className="btn-primaire">
                {envoi ? "Enregistrement…" : "Enregistrer et voir les offres"}
              </button>
            </form>

            <Suggestions donnees={recommandations} />
          </>
        )}
      </div>
    </Layout>
  );
}

/* ------------------------------------------------------------------ */

function Suggestions({ donnees }) {
  if (!donnees) return null;

  if (!donnees.profil_connu) {
    return (
      <EtatVide
        titre="Renseignez vos compétences pour commencer"
        description="Dès que le formulaire est enregistré, les offres les plus
                     proches de votre profil apparaissent ici."
      />
    );
  }

  if (!donnees.offres.length) {
    return (
      <EtatVide
        titre="Aucune offre ne correspond pour l'instant"
        description="Élargissez la ville ou le type de contrat, ou revenez plus
                     tard : de nouvelles offres sont publiées régulièrement."
        action={<Link href="/offres" className="btn-secondaire mt-2">Voir toutes les offres</Link>}
      />
    );
  }

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold text-sm">
          Offres proches de votre profil
          {" "}
          <span className="font-normal text-txt2">
            — {donnees.offres.length} sur {donnees.total_examinees} examinées
          </span>
        </h2>
        <Link href="/offres" className="text-[12.5px] text-accent hover:text-cyan">
          Voir toutes les offres →
        </Link>
      </div>

      <div className="space-y-3">
        {donnees.offres.map((o, rang) => (
          <Suggestion key={o.offre.id} suggestion={o} rang={rang} />
        ))}
      </div>

      <p className="text-[11.5px] text-txt2 leading-relaxed max-w-2xl pt-1">
        {donnees.lecture}
      </p>
    </section>
  );
}

function Suggestion({ suggestion: s, rang }) {
  const niveau = CORRESPONDANCE[s.correspondance] || CORRESPONDANCE.eloignee;

  return (
    <article
      className="carte carte-reactive p-5 entree"
      style={{ animationDelay: retard(rang, 70) }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Link
            href={`/offres/${s.offre.id}`}
            className="font-semibold hover:text-accent transition-colors"
          >
            {s.offre.titre}
          </Link>
          <p className="text-[12.5px] text-txt2 mt-0.5">
            {[s.offre.entreprise, s.offre.lieu, s.offre.contrat, s.offre.mode_travail]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <span className={`chip border text-[11px] font-medium shrink-0 ${niveau.style}`}>
          {niveau.libelle}
        </span>
      </div>

      {(s.competences_reconnues.length > 0 || s.competences_manquantes.length > 0) && (
        <div className="flex flex-wrap gap-1.5 mt-3.5">
          {s.competences_reconnues.map((c) => (
            <span key={c} className="chip bg-succes/10 text-succes">✓ {c}</span>
          ))}
          {s.competences_manquantes.map((c) => (
            <span key={c} className="chip bg-bordure/50 text-txt2" title="Non retrouvée dans votre profil">
              + {c}
            </span>
          ))}
        </div>
      )}

      {s.competences_manquantes.length > 0 && (
        <p className="text-[11.5px] text-txt2 mt-2.5">
          Il vous manque {s.competences_manquantes.length} compétence
          {s.competences_manquantes.length > 1 ? "s" : ""} pour cette offre —
          vous pouvez postuler malgré tout, le recruteur décide.
        </p>
      )}
    </article>
  );
}
