/**
 * Contrôle des dossiers : anomalies relevées sur les candidatures.
 *
 * L'écran est conçu autour d'une idée : un signalement n'est pas un verdict.
 * Chaque anomalie affiche donc le motif exact et les éléments qui l'ont
 * déclenchée, et la seule action possible est de trancher — confirmer ou
 * écarter — en laissant une trace. Écarter exige un motif : c'est la décision
 * qu'il faudra pouvoir justifier plus tard.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";
import { retard } from "@/lib/mouvement";

const LIBELLE_TYPE = {
  identite_divergente: "Identité divergente",
  email_divergent: "Adresse électronique divergente",
  email_tiers: "Adresse d'un autre compte",
  telephone_partage: "Numéro déjà rattaché",
  document_duplique: "Document dupliqué",
  document_similaire: "Document très proche d'un autre",
  chronologie_incoherente: "Chronologie incohérente",
  redaction_assistee: "Indices de rédaction assistée",
  fichier_suspect: "Fichier suspect",
};

const LIBELLE_SEVERITE = {
  alerte: "Alerte",
  attention: "Vigilance",
  information: "Information",
};

const STYLE_SEVERITE = {
  alerte: "bg-erreur/12 text-erreur border-erreur/35",
  attention: "bg-alerte/12 text-alerte border-alerte/35",
  information: "bg-accent/10 text-accent border-accent/30",
};

const LIBELLE_STATUT = {
  nouveau: "À examiner",
  examine: "En cours d'examen",
  confirme: "Confirmé",
  ecarte: "Écarté",
};

const ONGLETS = [
  { cle: "a_traiter", libelle: "À traiter" },
  { cle: "alerte", libelle: "Alertes" },
  { cle: "traites", libelle: "Traités" },
  { cle: "tous", libelle: "Tous" },
];

export default function Signalements() {
  const { chargement: garde } = useGarde(["recruiter", "admin"]);
  const [signalements, setSignalements] = useState([]);
  const [compteurs, setCompteurs] = useState({});
  const [onglet, setOnglet] = useState("a_traiter");
  const [chargement, setChargement] = useState(true);
  const [erreur, setErreur] = useState(null);

  const charger = useCallback(async () => {
    setChargement(true);
    try {
      const donnees = await api.signalements();
      setSignalements(donnees.signalements || []);
      setCompteurs(donnees.compteurs || {});
      setErreur(null);
    } catch (e) {
      setErreur(e.message);
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => {
    charger();
  }, [charger]);

  const trancher = async (signalement, statut, commentaire) => {
    // Mise à jour optimiste : la liste réagit immédiatement, le serveur confirme.
    setSignalements((liste) =>
      liste.map((s) => (s.id === signalement.id ? { ...s, statut } : s))
    );
    try {
      await api.traiterSignalement(signalement.id, statut, commentaire);
      charger();
    } catch (e) {
      setErreur(e.message);
      charger();
    }
  };

  const visibles = signalements.filter((s) => {
    if (onglet === "a_traiter") return ["nouveau", "examine"].includes(s.statut);
    if (onglet === "alerte") return s.severite === "alerte";
    if (onglet === "traites") return ["confirme", "ecarte"].includes(s.statut);
    return true;
  });

  if (garde) return null;

  return (
    <Layout titre="Contrôle des dossiers">
        <div className="space-y-5">
          <header className="space-y-1.5">
            <h1 className="text-xl font-bold">Contrôle des dossiers</h1>
            <p className="text-[13px] text-txt2 leading-relaxed max-w-3xl">
              Les anomalies relevées automatiquement sur les candidatures sont
              rassemblées ici. Aucune ne constitue une preuve : un nom d'épouse,
              une translittération ou un curriculum rédigé par un cabinet
              déclenchent les mêmes contrôles qu'une usurpation. À vous de
              trancher, en laissant une trace de votre décision.
            </p>
          </header>

          <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Carte libelle="Signalements" valeur={compteurs.total ?? 0} />
            <Carte libelle="À traiter" valeur={compteurs.a_traiter ?? 0} accent="alerte" />
            <Carte libelle="Alertes" valeur={compteurs.alertes ?? 0} accent="erreur" />
            <Carte libelle="Nouveaux" valeur={compteurs.nouveaux ?? 0} />
          </section>

          <nav className="flex gap-1 border-b border-bordure" role="tablist">
            {ONGLETS.map((o) => (
              <button
                key={o.cle}
                role="tab"
                aria-selected={onglet === o.cle}
                onClick={() => setOnglet(o.cle)}
                className={`px-3.5 py-2 text-[13px] font-medium border-b-2 -mb-px transition-colors ${
                  onglet === o.cle
                    ? "border-accent text-txt"
                    : "border-transparent text-txt2 hover:text-txt"
                }`}
              >
                {o.libelle}
              </button>
            ))}
          </nav>

          {erreur && (
            <p className="rounded-[10px] border border-erreur/40 bg-erreur/10 p-3 text-[13px] text-erreur">
              {erreur}
            </p>
          )}

          {chargement ? (
            <p className="text-sm text-txt2">Chargement…</p>
          ) : visibles.length === 0 ? (
            <p className="rounded-xl2 border border-bordure bg-surface2/50 p-8 text-center text-sm text-txt2">
              Aucun signalement dans cette vue. Les contrôles s'exécutent à
              chaque dépôt de candidature et à chaque réanalyse.
            </p>
          ) : (
            <ul className="space-y-3">
              {visibles.map((s, rang) => (
                <Signalement
                  key={s.id}
                  signalement={s}
                  onTrancher={trancher}
                  rang={rang}
                />
              ))}
            </ul>
          )}
        </div>
    </Layout>
  );
}

function Carte({ libelle, valeur, accent }) {
  const couleur =
    accent === "erreur" ? "text-erreur" : accent === "alerte" ? "text-alerte" : "text-txt";
  return (
    <div className="rounded-xl2 border border-bordure bg-surface2/50 p-3.5">
      <p className={`text-2xl font-bold ${couleur}`}>{valeur}</p>
      <p className="text-[11.5px] text-txt2 mt-0.5">{libelle}</p>
    </div>
  );
}

function Signalement({ signalement: s, onTrancher, rang = 0 }) {
  const [motif, setMotif] = useState("");
  const [saisieOuverte, setSaisieOuverte] = useState(false);
  const traite = ["confirme", "ecarte"].includes(s.statut);
  const details = s.details || {};

  return (
    <li
      className="rounded-xl2 border border-bordure bg-surface p-4 space-y-3 entree"
      style={{ animationDelay: retard(rang, 60) }}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`chip border text-[11px] font-semibold ${STYLE_SEVERITE[s.severite]}`}
            >
              {LIBELLE_SEVERITE[s.severite] || s.severite}
            </span>
            <span className="text-[13px] font-semibold">
              {LIBELLE_TYPE[s.type] || s.type}
            </span>
          </div>
          <p className="text-[13px] text-txt2">{s.message}</p>
        </div>

        <span
          className={`chip text-[11px] shrink-0 ${
            traite ? "bg-bordure/40 text-txt2" : "bg-accent/15 text-accent"
          }`}
        >
          {LIBELLE_STATUT[s.statut] || s.statut}
        </span>
      </div>

      {s.candidature && (
        <p className="text-[12px] text-txt2">
          {s.candidature.candidat} — {s.candidature.offre}
          {s.candidature.score != null && ` · note ${Math.round(s.candidature.score)}/100`}
          {" · "}
          <Link href="/candidatures" className="text-accent hover:text-cyan">
            ouvrir la candidature →
          </Link>
        </p>
      )}

      {/* Les éléments déclencheurs : ce qui rend l'observation vérifiable */}
      {Object.keys(details).length > 0 && (
        <details className="rounded-[10px] border border-bordure bg-fond/40 px-3 py-2">
          <summary className="text-[11.5px] text-txt2 cursor-pointer hover:text-txt">
            Éléments relevés
          </summary>
          <dl className="mt-2 space-y-1">
            {Object.entries(details).map(([cle, valeur]) => (
              <div key={cle} className="flex gap-2 text-[11.5px]">
                <dt className="text-txt2 shrink-0 min-w-[9rem]">
                  {cle.replaceAll("_", " ")}
                </dt>
                <dd className="text-txt">
                  {Array.isArray(valeur) ? valeur.join(", ") : String(valeur)}
                </dd>
              </div>
            ))}
          </dl>
        </details>
      )}

      {traite ? (
        <p className="text-[11.5px] text-txt2 border-t border-bordure pt-2.5">
          {LIBELLE_STATUT[s.statut]} par {s.reviewed_by || "un utilisateur"}
          {s.commentaire && ` — « ${s.commentaire} »`}
        </p>
      ) : (
        <div className="border-t border-bordure pt-3 space-y-2">
          {saisieOuverte && (
            <input
              className="champ text-[13px]"
              placeholder="Motif de l'écartement (obligatoire)"
              value={motif}
              onChange={(e) => setMotif(e.target.value)}
              aria-label="Motif de l'écartement"
            />
          )}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => onTrancher(s, "confirme", motif)}
              className="btn-secondaire text-[12.5px] border-erreur/40 text-erreur hover:bg-erreur/10"
            >
              Confirmer l'anomalie
            </button>
            <button
              onClick={() => {
                if (!saisieOuverte) return setSaisieOuverte(true);
                if (motif.trim()) onTrancher(s, "ecarte", motif.trim());
              }}
              className="btn-secondaire text-[12.5px]"
              title="Un motif est requis pour écarter un signalement"
            >
              {saisieOuverte ? "Valider l'écartement" : "Écarter"}
            </button>
            {s.statut === "nouveau" && (
              <button
                onClick={() => onTrancher(s, "examine", "")}
                className="text-[12.5px] text-txt2 hover:text-txt px-2"
              >
                Marquer en cours d'examen
              </button>
            )}
          </div>
        </div>
      )}
    </li>
  );
}
