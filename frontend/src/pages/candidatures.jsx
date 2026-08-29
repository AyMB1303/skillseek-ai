                                                            /** Candidatures classées : onglets RG-01, tri, drawer d'explicabilité, actions. */
import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur, EtatVide, BadgeStatut, Drawer, useToast, STATUTS } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api, telechargerFichier } from "@/lib/api";
import { couleurScore, SEUIL_RETENU, PLAFOND_TOP } from "@/lib/scoring";
import { useCompteur, retard } from "@/lib/mouvement";

const ONGLETS = [
  { cle: "toutes", libelle: "Toutes" },
  { cle: "top", libelle: `Top ${PLAFOND_TOP} IA` },
  { cle: "ecartees", libelle: `Écartées (< ${SEUIL_RETENU})` },
  { cle: "attente", libelle: "Sans score" },
];

export default function Candidatures() {
  const { chargement: garde } = useGarde(["recruiter"]);
  const router = useRouter();
  // Filtre par offre, transmis par l'écran « Mes offres ». Le passer dans
  // l'adresse plutôt que dans un état local rend la vue partageable et
  // rechargeable : un recruteur peut envoyer le lien à un collègue.
  const offreFiltree = router.query.offre ? Number(router.query.offre) : null;
  const { notifier } = useToast();
  const [candidatures, setCandidatures] = useState([]);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");
  const [onglet, setOnglet] = useState("toutes");
  const [tri, setTri] = useState({ champ: "score", sens: "desc" });
  const [selection, setSelection] = useState(null);
  const [filtres, setFiltres] = useState({
    recherche: "",
    competence: "",
    tranche: "",
    signalees: false,
  });

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

  // Application de la règle RG-01 puis du tri demandé.
  // Une candidature dont le score est null n'est PAS écartée : elle n'a pas
  // encore été analysée (module d'extraction du CV, Sprint 3).
  const groupes = useMemo(() => {
    const perimetre = offreFiltree
      ? candidatures.filter((c) => c.offer?.id === offreFiltree)
      : candidatures;
    const analysees = perimetre.filter((c) => c.score != null);
    return {
      toutes: perimetre,
      top: [...analysees.filter((c) => c.score >= SEUIL_RETENU)]
        .sort((a, b) => b.score - a.score)
        .slice(0, PLAFOND_TOP),
      ecartees: analysees.filter((c) => c.score < SEUIL_RETENU),
      attente: perimetre.filter((c) => c.score == null),
    };
  }, [candidatures, offreFiltree]);

  // Intitulé de l'offre filtrée, lu dans les candidatures déjà chargées :
  // inutile d'interroger le serveur pour un libellé qu'on possède.
  const titreOffreFiltree = useMemo(
    () =>
      candidatures.find((c) => c.offer?.id === offreFiltree)?.offer?.title || null,
    [candidatures, offreFiltree]
  );

  // Compétences réellement présentes dans le lot, pour ne proposer que des
  // filtres qui donneront un résultat.
  const competencesDisponibles = useMemo(() => {
    const toutes = new Set();
    candidatures.forEach((c) =>
      (c.score_details?.profil_ats?.skills || []).forEach((s) => toutes.add(s))
    );
    return [...toutes].sort();
  }, [candidatures]);

  const affichees = useMemo(() => {
    const q = filtres.recherche.trim().toLowerCase();
    const filtrees = groupes[onglet].filter((c) => {
      if (q) {
        const cible = `${c.candidate?.full_name || ""} ${c.candidate?.email || ""}`.toLowerCase();
        if (!cible.includes(q)) return false;
      }
      if (filtres.competence) {
        const detenues = c.score_details?.profil_ats?.skills || [];
        if (!detenues.includes(filtres.competence)) return false;
      }
      if (filtres.tranche && c.score != null) {
        const [min, max] = filtres.tranche.split("-").map(Number);
        if (c.score < min || c.score > max) return false;
      }
      if (filtres.tranche && c.score == null) return false;
      if (filtres.signalees) {
        const actifs = (c.signalements || []).filter((s) => s.statut !== "ecarte");
        if (actifs.length === 0) return false;
      }
      return true;
    });

    return [...filtrees].sort((a, b) => {
      const va = tri.champ === "score" ? a.score ?? -1 : a.candidate?.full_name || "";
      const vb = tri.champ === "score" ? b.score ?? -1 : b.candidate?.full_name || "";
      const cmp = typeof va === "number" ? va - vb : String(va).localeCompare(String(vb));
      return tri.sens === "asc" ? cmp : -cmp;
    });
  }, [groupes, onglet, tri, filtres]);

  const filtreActif =
    filtres.recherche || filtres.competence || filtres.tranche || filtres.signalees;

  const compteurs = useMemo(
    () => Object.fromEntries(Object.entries(groupes).map(([k, v]) => [k, v.length])),
    [groupes]
  );

  const basculerTri = (champ) =>
    setTri((t) => ({ champ, sens: t.champ === champ && t.sens === "desc" ? "asc" : "desc" }));

  /** Changement de statut avec mise à jour optimiste et possibilité d'annuler. */
  const changerStatut = async (candidature, statut) => {
    const ancien = candidature.status;
    setCandidatures((l) => l.map((c) => (c.id === candidature.id ? { ...c, status: statut } : c)));
    setSelection((s) => (s?.id === candidature.id ? { ...s, status: statut } : s));
    try {
      await api.changerStatut(candidature.id, statut);
      notifier(`${candidature.candidate?.full_name} → ${STATUTS[statut].libelle}`, {
        annuler: async () => {
          setCandidatures((l) => l.map((c) => (c.id === candidature.id ? { ...c, status: ancien } : c)));
          await api.changerStatut(candidature.id, ancien).catch(() => {});
        },
      });
    } catch (e) {
      setCandidatures((l) => l.map((c) => (c.id === candidature.id ? { ...c, status: ancien } : c)));
      notifier(e.message, { type: "erreur" });
    }
  };

  if (garde) return null;

  return (
    <Layout titre="Candidatures" compteurCandidatures={candidatures.length}>
      {/* Filtre venu de « Mes offres » : dit toujours ce qu'on regarde, et
          comment en sortir. Un filtre invisible fait croire à une base vide. */}
      {offreFiltree && (
        <div className="flex flex-wrap items-center gap-2 mb-4 rounded-[10px] border border-accent/30 bg-accent/8 px-3.5 py-2.5">
          <span className="text-[13px]">
            Candidatures pour{" "}
            <strong>{titreOffreFiltree || `l'offre nº${offreFiltree}`}</strong>
          </span>
          <span className="text-[12px] text-txt2">
            · {groupes.toutes.length} sur {candidatures.length} au total
          </span>
          <Link
            href="/candidatures"
            className="ml-auto text-[12.5px] text-accent hover:text-cyan"
          >
            Voir toutes les candidatures →
          </Link>
        </div>
      )}

      {/* Onglets : traduisent la règle RG-01 */}
      <div className="flex gap-1 border-b border-bordure mb-5">
        {ONGLETS.map((o) => (
          <button
            key={o.cle}
            onClick={() => setOnglet(o.cle)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              onglet === o.cle ? "border-accent text-txt" : "border-transparent text-txt2 hover:text-txt"
            }`}
            aria-selected={onglet === o.cle}
            role="tab"
          >
            {o.libelle}
            <span className="ml-2 text-xs text-txt2">{compteurs[o.cle]}</span>
          </button>
        ))}
      </div>

      {onglet === "ecartees" && (
        <p className="text-xs text-txt2 mb-4 bg-surface border border-bordure rounded-[10px] px-3.5 py-2.5">
          Ces candidatures sont écartées du classement mais conservées. Vous pouvez en repêcher une à tout moment :
          la décision finale vous appartient.
        </p>
      )}
      {onglet === "attente" && (
        <p className="text-xs text-txt2 mb-4 bg-surface border border-bordure rounded-[10px] px-3.5 py-2.5">
          Ces candidatures n'ont pas de score : le document n'a pas pu être lu automatiquement
          (scan illisible, PDF protégé). Elles ne sont ni retenues ni écartées — ouvrez le détail
          pour relancer l'analyse ou saisir le profil à la main.
        </p>
      )}

      {/* Filtres. À partir de quelques dizaines de candidatures, la liste
          seule ne suffit plus : le recruteur cherche « qui connaît Docker »
          ou « qui a été signalé », pas « la 47ᵉ ligne ». */}
      {etat === "ok" && groupes.toutes.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <input
            type="search"
            value={filtres.recherche}
            onChange={(e) => setFiltres({ ...filtres, recherche: e.target.value })}
            placeholder="Nom ou adresse électronique…"
            aria-label="Rechercher un candidat"
            className="champ max-w-[15rem] py-2 text-[13px]"
          />

          <select
            value={filtres.competence}
            onChange={(e) => setFiltres({ ...filtres, competence: e.target.value })}
            aria-label="Filtrer par compétence détenue"
            className="champ w-auto py-2 text-[13px]"
          >
            <option value="">Toute compétence</option>
            {competencesDisponibles.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          <select
            value={filtres.tranche}
            onChange={(e) => setFiltres({ ...filtres, tranche: e.target.value })}
            aria-label="Filtrer par tranche de note"
            className="champ w-auto py-2 text-[13px]"
          >
            <option value="">Toute note</option>
            <option value="85-100">85 et plus</option>
            <option value="70-84">70 à 84</option>
            <option value="50-69">50 à 69</option>
            <option value="0-49">Moins de 50</option>
          </select>

          <button
            onClick={() => setFiltres({ ...filtres, signalees: !filtres.signalees })}
            aria-pressed={filtres.signalees}
            className={`chip text-[12px] border transition-colors ${
              filtres.signalees
                ? "bg-alerte/15 text-alerte border-alerte/40"
                : "bg-surface text-txt2 border-bordure hover:text-txt"
            }`}
          >
            Dossiers signalés
          </button>

          {filtreActif && (
            <button
              onClick={() =>
                setFiltres({ recherche: "", competence: "", tranche: "", signalees: false })
              }
              className="text-[12.5px] text-txt2 hover:text-txt px-1"
            >
              Réinitialiser
            </button>
          )}

          <span className="ml-auto text-[12px] text-txt2">
            {affichees.length} affichée{affichees.length > 1 ? "s" : ""}
          </span>
        </div>
      )}

      {etat === "chargement" && <Chargement lignes={5} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" && (
        affichees.length === 0 ? (
          <EtatVide titre="Aucune candidature" description="Rien à afficher dans cet onglet pour le moment." />
        ) : (
          <div className="carte overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-txt2 text-xs border-b border-bordure">
                  <ThTri champ="nom" tri={tri} onClick={basculerTri}>Candidat</ThTri>
                  <th className="px-5 py-3 font-medium">Offre</th>
                  <ThTri champ="score" tri={tri} onClick={basculerTri}>Score</ThTri>
                  <th className="px-5 py-3 font-medium">Statut</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody>
                {affichees.map((c, rang) => {
                  const coul = couleurScore(c.score);
                  const trouvees = c.score_details?.competences_trouvees || [];
                  const manquantes = c.score_details?.competences_manquantes || [];
                  return (
                    // Le decalage rend le changement d'onglet ou de filtre
                    // perceptible : la liste se recompose au lieu de sauter.
                    <tr
                      key={c.id}
                      className="border-b border-bordure last:border-0 hover:bg-surface2/60 transition-colors entree"
                      style={{ animationDelay: retard(rang, 22, 260) }}
                    >
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-bordure text-cyan grid place-items-center text-[11px] font-bold shrink-0">
                            {(c.candidate?.full_name || "?").split(" ").map((m) => m[0]).slice(0, 2).join("")}
                          </div>
                          <div className="min-w-0">
                            <div className="font-medium truncate flex items-center gap-1.5">
                              {c.candidate?.full_name}
                              <MarqueurControle signalements={c.signalements} />
                              <MarqueurAttente candidature={c} />
                            </div>
                            <div className="text-xs text-txt2 truncate">{c.candidate?.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-txt2">{c.offer?.title}</td>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <JaugeScore score={c.score} />
                          <div className="flex gap-1 flex-wrap max-w-[180px]">
                            {trouvees.slice(0, 2).map((s) => (
                              <span key={s} className="chip bg-succes/10 text-succes text-[10px]">{s}</span>
                            ))}
                            {manquantes.slice(0, 1).map((s) => (
                              <span key={s} className="chip bg-bordure/50 text-txt2 text-[10px]">{s}</span>
                            ))}
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3"><BadgeStatut statut={c.status} /></td>
                      <td className="px-5 py-3 text-right">
                        <button onClick={() => setSelection(c)} className="text-xs text-accent hover:text-cyan">
                          Détails
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )
      )}

      {/* ---------- Drawer d'explicabilité ---------- */}
      <Drawer
        ouvert={!!selection}
        onFermer={() => setSelection(null)}
        titre={selection?.candidate?.full_name || ""}
      >
        {selection && (
          <DetailCandidature
            candidature={selection}
            onStatut={changerStatut}
            onAnalyse={(maj) => {
              setCandidatures((l) => l.map((c) => (c.id === maj.id ? maj : c)));
              setSelection(maj);
              notifier(`Score calculé : ${maj.score}/100`);
            }}
          />
        )}
      </Drawer>
    </Layout>
  );
}

function ThTri({ champ, tri, onClick, children }) {
  const actif = tri.champ === champ;
  return (
    <th className="px-5 py-3 font-medium">
      <button onClick={() => onClick(champ)} className="flex items-center gap-1 hover:text-txt">
        {children}
        <span className={actif ? "text-accent" : "text-bordure"}>{actif && tri.sens === "asc" ? "▲" : "▼"}</span>
      </button>
    </th>
  );
}

/** Chiffre du score qui monte jusqu'à sa valeur, sans jamais la dépasser. */
function CompteurScore({ valeur }) {
  const affiche = useCompteur(valeur, { duree: 950 });
  return <span aria-label={`${valeur} sur 100`}>{affiche}</span>;
}

/**
 * Mise en correspondance des compétences : ce que l'offre exige, ce que le CV
 * porte, et le lien entre les deux.
 *
 * Une liste de pastilles vertes et rouges dit qu'une compétence manque. Elle
 * ne dit pas *sur quoi* le rapprochement s'est fait. Survoler une exigence
 * éclaire ici la compétence correspondante relevée dans le document, et
 * estompe le reste : le recruteur voit d'un coup d'œil ce que le moteur a
 * apparié, et peut le contester.
 *
 * Les compétences absentes restent affichées. Les masquer donnerait un profil
 * plus flatteur qu'il ne l'est.
 */
function CorrespondanceCompetences({ details: d, nonAnalysee }) {
  const [survolee, setSurvolee] = useState(null);

  const requises = [
    ...(d.competences_trouvees || []).map((s) => ({ nom: s, trouvee: true })),
    ...(d.competences_manquantes || []).map((s) => ({ nom: s, trouvee: false })),
  ];
  const detectees = (d.profil_ats?.skills || d.profil_analyse?.skills || []).slice(0, 24);

  if (!requises.length) {
    return (
      <div>
        <h3 className="text-xs font-semibold text-txt2 mb-2">Compétences obligatoires</h3>
        <p className="text-xs text-txt2">
          {nonAnalysee
            ? "Lancez l'analyse ci-dessus pour obtenir le détail des compétences."
            : "Aucune compétence obligatoire n'était définie sur cette offre."}
        </p>
      </div>
    );
  }

  // Un survol n'a d'effet que s'il existe une contrepartie à éclairer.
  const eclairer = (nom) =>
    survolee && survolee.toLowerCase() === (nom || "").toLowerCase();
  const estompee = (nom) => survolee && !eclairer(nom);

  const classe = (nom, base) =>
    `chip correspondance ${base} ${eclairer(nom) ? "correspondance-active" : ""} ${
      estompee(nom) ? "correspondance-effacee" : ""
    }`;

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <h3 className="text-xs font-semibold text-txt2 mb-2">
          Exigé par l'offre
          <span className="font-normal"> ({requises.filter((r) => r.trouvee).length}/{requises.length})</span>
        </h3>
        <div className="flex flex-wrap gap-1.5">
          {requises.map((r, i) => (
            <button
              key={r.nom}
              type="button"
              onMouseEnter={() => r.trouvee && setSurvolee(r.nom)}
              onMouseLeave={() => setSurvolee(null)}
              onFocus={() => r.trouvee && setSurvolee(r.nom)}
              onBlur={() => setSurvolee(null)}
              title={
                r.trouvee
                  ? "Relevée dans le CV — survolez pour voir la correspondance"
                  : "Absente du CV"
              }
              className={`entree ${classe(
                r.trouvee ? r.nom : null,
                r.trouvee ? "bg-succes/10 text-succes" : "bg-erreur/10 text-erreur"
              )}`}
              style={{ animationDelay: retard(i, 40) }}
            >
              {r.trouvee ? "✓" : "✗"} {r.nom}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-txt2 mb-2">
          Relevé dans le CV
          {detectees.length > 0 && <span className="font-normal"> ({detectees.length})</span>}
        </h3>
        {detectees.length === 0 ? (
          <p className="text-xs text-txt2">
            Aucune compétence n'a pu être relevée dans le document.
          </p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {detectees.map((s, i) => (
              <span
                key={s}
                onMouseEnter={() => setSurvolee(s)}
                onMouseLeave={() => setSurvolee(null)}
                className={`entree ${classe(s, "bg-surface2 border border-bordure text-txt2")}`}
                style={{ animationDelay: retard(i, 25) }}
              >
                {s}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Jauge circulaire du score.
 *
 * `anime` réserve le décompte au panneau de détail. Dans la liste, une
 * trentaine de jauges qui comptent ensemble transformeraient une page de
 * travail en tableau de bord d'aéroport : l'arc s'y remplit simplement, sans
 * chiffre qui défile.
 *
 * La valeur exacte est portée par `aria-label` dès le premier rendu : ce que
 * lit une synthèse vocale ne dépend pas de l'avancement de l'animation.
 */
function JaugeScore({ score, taille = 44, anime = false }) {
  const coul = couleurScore(score);
  const affiche = useCompteur(score, { duree: 950, actif: anime });
  const r = 15;
  const circ = 2 * Math.PI * r;
  const pct = (anime ? affiche : score) ?? 0;

  return (
    <div
      className="relative shrink-0"
      style={{ width: taille, height: taille }}
      title={`Score : ${score ?? "non calculé"}/100`}
      role="img"
      aria-label={score == null ? "Score non calculé" : `Score ${score} sur 100`}
    >
      <svg viewBox="0 0 40 40" className="w-full h-full -rotate-90" aria-hidden="true">
        <circle cx="20" cy="20" r={r} fill="none" className="stroke-bordure" strokeWidth="4" />
        <circle
          cx="20" cy="20" r={r} fill="none" stroke={coul.anneau} strokeWidth="4" strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={circ - (pct / 100) * circ}
          style={{ transition: anime ? "none" : "stroke-dashoffset 700ms cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <span
        className={`absolute inset-0 grid place-items-center font-bold ${coul.texte}`}
        style={{ fontSize: taille > 60 ? 18 : 11 }}
        aria-hidden="true"
      >
        {score == null ? "—" : anime ? affiche : score}
      </span>
    </div>
  );
}

/**
 * Repère discret dans la liste : un triangle coloré à côté du nom.
 *
 * Il doit se voir sans hurler. Le survol donne le motif, ce qui évite au
 * recruteur d'ouvrir chaque dossier pour savoir de quoi il retourne.
 */
function MarqueurControle({ signalements }) {
  const anomalies = (signalements || []).filter((s) => s.statut !== "ecarte");
  if (anomalies.length === 0) return null;

  const grave = anomalies.some((s) => s.severite === "alerte");
  const motifs = anomalies
    .map((s) => LIBELLE_CONTROLE[s.type] || s.type)
    .join(" · ");

  return (
    <span
      title={`${anomalies.length} point(s) de vigilance : ${motifs}`}
      aria-label={`Dossier signalé : ${motifs}`}
      className={`shrink-0 ${grave ? "text-erreur" : "text-alerte"}`}
    >
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
        <path d="M12 3l9 16H3z" /><path d="M12 9v4" /><path d="M12 16.5h.01" />
      </svg>
    </span>
  );
}

// Au-delà de ce délai sans décision, une candidature est signalée comme
// dormante. Dix jours ouvrés est le seuil au-delà duquel un candidat
// considère généralement qu'il n'aura pas de réponse.
const JOURS_AVANT_RELANCE = 10;

/** Signale une candidature laissée sans décision depuis trop longtemps. */
function MarqueurAttente({ candidature }) {
  if (!["received", "under_review"].includes(candidature.status)) return null;

  const jours = Math.floor(
    (Date.now() - new Date(candidature.created_at).getTime()) / 86400000
  );
  if (jours < JOURS_AVANT_RELANCE) return null;

  return (
    <span
      title={`Sans décision depuis ${jours} jours`}
      aria-label={`En attente depuis ${jours} jours`}
      className="chip bg-alerte/15 text-alerte text-[10px] py-0 shrink-0"
    >
      {jours} j
    </span>
  );
}

const LIBELLE_CONTROLE = {
  identite_divergente: "le nom du CV ne correspond pas au compte",
  email_divergent: "adresse électronique différente de celle du compte",
  email_tiers: "l'adresse du CV appartient à un autre compte",
  telephone_partage: "numéro déjà rattaché à un autre candidat",
  document_duplique: "CV identique à celui d'un autre candidat",
  document_similaire: "CV très proche de celui d'un autre candidat",
  chronologie_incoherente: "dates du parcours incohérentes",
  redaction_assistee: "indices de rédaction assistée",
  fichier_suspect: "fichier suspect",
};

/**
 * Avertissement affiché sur une candidature comportant des anomalies.
 *
 * Le parti pris est important : la note n'est pas touchée. Un candidat
 * excellent dont le dossier présente une anomalie reste noté 92, et le
 * recruteur voit à la fois l'excellence et le doute. Baisser la note
 * mélangerait deux jugements de nature différente — l'adéquation au poste et
 * la fiabilité du dossier — et priverait le recruteur de l'un des deux.
 */
function AvertissementControles({ signalements }) {
  const anomalies = (signalements || []).filter((s) => s.statut !== "ecarte");
  if (anomalies.length === 0) return null;

  const grave = anomalies.some((s) => s.severite === "alerte");
  const style = grave
    ? "border-erreur/50 bg-erreur/10"
    : "border-alerte/50 bg-alerte/10";
  const couleurTitre = grave ? "text-erreur" : "text-alerte";

  return (
    <div className={`rounded-[10px] border p-3.5 space-y-2 ${style}`} role="alert">
      <div className="flex items-center gap-2">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"
             className={couleurTitre}>
          <path d="M12 3l9 16H3z" /><path d="M12 9v4" /><path d="M12 16.5h.01" />
        </svg>
        <p className={`text-xs font-semibold ${couleurTitre}`}>
          {grave ? "Dossier à vérifier avant tout entretien" : "Point de vigilance sur ce dossier"}
        </p>
      </div>

      <ul className="space-y-1">
        {anomalies.map((s) => (
          <li key={s.id} className="text-[12.5px] text-txt2">
            • <span className="text-txt">{LIBELLE_CONTROLE[s.type] || s.type}</span>
            {" — "}{s.message}
          </li>
        ))}
      </ul>

      <p className="text-[11px] text-txt2 border-t border-bordure/60 pt-2 leading-snug">
        La note reste calculée normalement : ces observations portent sur la
        fiabilité du dossier, pas sur l'adéquation au poste. Aucune ne
        constitue une preuve.{" "}
        <Link href="/signalements" className="text-accent hover:text-cyan">
          Traiter le signalement →
        </Link>
      </p>
    </div>
  );
}

/**
 * Fiche d'évaluation imprimable.
 *
 * Une décision de recrutement se partage souvent avec un manager qui n'a pas
 * de compte sur la plateforme. Plutôt que de lui envoyer une capture d'écran,
 * cette fiche reprend le raisonnement complet — profil reconstitué, détail du
 * calcul, réserves, signalements — dans un document qu'il peut lire, annoter
 * et archiver.
 *
 * L'impression se fait par le navigateur, sur un document construit à la
 * volée : aucune bibliothèque, et le résultat est identique à ce qui est
 * affiché à l'écran.
 */
function ImpressionFiche({ candidature }) {
  const imprimer = () => {
    const d = candidature.score_details || {};
    const profil = d.profil_ats || {};
    const anomalies = (candidature.signalements || []).filter(
      (s) => s.statut !== "ecarte"
    );

    const ligne = (libelle, valeur) =>
      valeur ? `<tr><th>${libelle}</th><td>${valeur}</td></tr>` : "";

    const html = `<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<title>Fiche — ${candidature.candidate?.full_name || ""}</title>
<style>
  body { font-family: Segoe UI, system-ui, sans-serif; color: #1F3A5F; margin: 2.5cm 2cm; line-height: 1.5; }
  h1 { font-size: 20px; margin: 0 0 2px; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .04em;
       color: #6B7A8F; margin: 22px 0 8px; border-bottom: 1px solid #DCE6EE; padding-bottom: 4px; }
  .entete { display: flex; justify-content: space-between; align-items: flex-start; }
  .note { font-size: 34px; font-weight: 700; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; font-weight: 500; color: #6B7A8F; width: 38%; padding: 3px 0; vertical-align: top; }
  td { padding: 3px 0; }
  ul { margin: 4px 0; padding-left: 18px; font-size: 13px; }
  .alerte { border: 1px solid #C1502E; background: #FDF2EF; padding: 10px 12px; border-radius: 6px; }
  .pied { margin-top: 30px; font-size: 11px; color: #6B7A8F; border-top: 1px solid #DCE6EE; padding-top: 8px; }
</style></head><body>

<div class="entete">
  <div>
    <h1>${candidature.candidate?.full_name || "Candidat"}</h1>
    <p style="margin:0;color:#6B7A8F;font-size:13px">
      ${candidature.offer?.title || ""} — candidature du
      ${new Date(candidature.created_at).toLocaleDateString("fr-FR")}
    </p>
  </div>
  <div class="note">${candidature.score ?? "—"}<span style="font-size:16px;color:#6B7A8F">/100</span></div>
</div>

${
  anomalies.length
    ? `<h2>Points de vigilance</h2><div class="alerte"><ul>${anomalies
        .map((s) => `<li>${s.message}</li>`)
        .join("")}</ul>
      <p style="margin:6px 0 0;font-size:11px">Ces observations portent sur la fiabilité du dossier,
      non sur l'adéquation au poste. Aucune ne constitue une preuve.</p></div>`
    : ""
}

<h2>Détail du calcul</h2>
<table>${(d.composantes || [])
      .map((c) => `<tr><th>${c.libelle}</th><td>${c.valeur} / ${c.max}</td></tr>`)
      .join("")}</table>

${
  d.eliminatoires?.length
    ? `<h2>Critères éliminatoires</h2><ul>${d.eliminatoires
        .map((m) => `<li>${m}</li>`)
        .join("")}</ul>`
    : ""
}
${
  d.reserves?.length
    ? `<h2>Réserves</h2><ul>${d.reserves.map((m) => `<li>${m}</li>`).join("")}</ul>`
    : ""
}

<h2>Profil reconstitué</h2>
<table>
  ${ligne("Expérience totale", profil.totalExperienceYears ? `${profil.totalExperienceYears} ans` : "")}
  ${ligne("Diplôme le plus élevé", profil.highestDegree)}
  ${ligne("Compétences détectées", (profil.skills || []).join(", "))}
  ${ligne("Langues", (profil.languages || []).map((l) => `${l.language} ${l.fluency || ""}`).join(", "))}
  ${ligne("Certifications", (profil.certificates || []).map((c) => c.name).join(", "))}
</table>

${
  (profil.work || []).length
    ? `<h2>Parcours</h2><ul>${profil.work
        .map(
          (p) =>
            `<li><strong>${p.position || "Poste"}</strong>${
              p.company ? ` — ${p.company}` : ""
            } (${p.startDate || "?"} → ${p.current ? "présent" : p.endDate || "?"})</li>`
        )
        .join("")}</ul>`
    : ""
}

<div class="pied">
  SkillSeek AI — fiche éditée le ${new Date().toLocaleDateString("fr-FR")}.
  La note est une aide à la décision produite automatiquement ; le choix final
  appartient au recruteur.
</div>
</body></html>`;

    const fenetre = window.open("", "_blank", "width=900,height=1000");
    if (!fenetre) return;
    fenetre.document.write(html);
    fenetre.document.close();
    // Laisser le navigateur peindre le document avant d'ouvrir l'impression,
    // sinon certaines feuilles de style ne sont pas encore appliquées.
    fenetre.setTimeout(() => fenetre.print(), 300);
  };

  return (
    <button
      onClick={imprimer}
      className="text-[12px] text-txt2 hover:text-accent transition-colors inline-flex items-center gap-1.5"
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
        <path d="M6 9V3h12v6" /><rect x="4" y="9" width="16" height="8" rx="2" />
        <path d="M8 17h8v4H8z" />
      </svg>
      Imprimer la fiche d'évaluation
    </button>
  );
}

/**
 * Grille d'entretien : critères et verdicts.
 *
 * Ces listes existent côté serveur, dans `models/evaluation.py`, et l'API les
 * expose par `/evaluations/grille` précisément pour éviter qu'elles soient
 * recopiées ici. Elles l'étaient malgré tout : ajouter un critère au serveur
 * n'aurait rien changé à l'écran, et le retirer aurait fait rejeter la saisie
 * avec un message incompréhensible.
 *
 * Le référentiel est donc chargé une fois puis partagé par toutes les fiches.
 * Les valeurs ci-dessous ne servent plus que de repli au premier rendu et si
 * l'appel échoue : la grille reste utilisable, ce qui vaut mieux qu'un écran
 * vide pendant un entretien.
 */
const CRITERES_PAR_DEFAUT = [
  { code: "competences_techniques", libelle: "Compétences techniques" },
  { code: "experience_pertinente", libelle: "Pertinence de l'expérience" },
  { code: "communication", libelle: "Communication" },
  { code: "motivation", libelle: "Motivation et projet" },
  { code: "adequation_equipe", libelle: "Adéquation à l'équipe" },
];

const VERDICTS_PAR_DEFAUT = [
  { code: "a_recruter", libelle: "À recruter" },
  { code: "reserve", libelle: "Sous réserve" },
  { code: "a_revoir", libelle: "À revoir plus tard" },
  { code: "non_retenu", libelle: "Non retenu" },
];

// Un seul appel pour toute la page, quel que soit le nombre de fiches
// ouvertes : la promesse est mémorisée, pas son résultat.
let promesseGrille = null;

function useGrilleEntretien() {
  const [grille, setGrille] = useState({
    criteres: CRITERES_PAR_DEFAUT,
    verdicts: VERDICTS_PAR_DEFAUT,
  });

  useEffect(() => {
    let actif = true;
    promesseGrille = promesseGrille || api.grilleEvaluation();
    promesseGrille
      .then((d) => {
        if (actif && d?.criteres?.length) {
          setGrille({ criteres: d.criteres, verdicts: d.verdicts });
        }
      })
      .catch(() => {
        // Le repli couvre exactement ce cas : on garde la grille par défaut.
        promesseGrille = null;
      });
    return () => {
      actif = false;
    };
  }, []);

  return grille;
}

/**
 * Compte rendu d'entretien.
 *
 * L'intérêt dépasse la prise de notes : en consignant l'appréciation portée
 * après l'entretien à côté de la note calculée avant, la plateforme se donne
 * le seul moyen honnête de savoir ce que vaut son propre classement — non pas
 * sur un corpus public, mais sur les candidats réellement reçus. L'écart entre
 * les deux est affiché sans complaisance, y compris quand il est défavorable
 * au système.
 */
function GrilleEntretien({ candidature }) {
  const { criteres, verdicts } = useGrilleEntretien();
  const [ouvert, setOuvert] = useState(false);
  const [evaluation, setEvaluation] = useState(null);
  const [notes, setNotes] = useState({});
  const [verdict, setVerdict] = useState("reserve");
  const [commentaire, setCommentaire] = useState("");
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    let actif = true;
    api
      .evaluation(candidature.id)
      .then((d) => {
        if (!actif || !d.evaluation) return;
        setEvaluation(d.evaluation);
        setNotes(d.evaluation.notes || {});
        setVerdict(d.evaluation.verdict);
        setCommentaire(d.evaluation.commentaire || "");
      })
      .catch(() => {});
    return () => {
      actif = false;
    };
  }, [candidature.id]);

  const enregistrer = async () => {
    setEnvoi(true);
    setErreur("");
    try {
      const d = await api.enregistrerEvaluation(candidature.id, {
        notes,
        verdict,
        commentaire,
      });
      setEvaluation(d.evaluation);
      setOuvert(false);
    } catch (e) {
      setErreur(e.message);
    } finally {
      setEnvoi(false);
    }
  };

  const renseignees = Object.keys(notes).length;

  return (
    <section className="border-t border-bordure pt-4 space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold text-txt2">Entretien</h3>
        <button
          onClick={() => setOuvert(!ouvert)}
          className="text-[12px] text-accent hover:text-cyan"
        >
          {ouvert ? "Replier" : evaluation ? "Modifier l'évaluation" : "Évaluer après entretien"}
        </button>
      </div>

      {/* Confrontation des deux jugements, une fois l'entretien consigné */}
      {evaluation && !ouvert && (
        <div className="rounded-[10px] border border-bordure bg-surface2/50 p-3 space-y-1.5">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="text-[13px] font-semibold">
              {evaluation.verdict_libelle}
            </span>
            <span className="text-[12px] text-txt2">
              moyenne {evaluation.moyenne}/5 · soit {evaluation.note_humaine_sur_100}/100
            </span>
          </div>
          {evaluation.ecart != null && (
            <p className="text-[11.5px] text-txt2 leading-snug">
              Le système avait attribué {Math.round(evaluation.score_systeme)}/100 :{" "}
              {evaluation.ecart === 0
                ? "les deux appréciations coïncident."
                : evaluation.ecart > 0
                ? `il a été ${evaluation.ecart} points plus généreux que vous.`
                : `il a été ${Math.abs(evaluation.ecart)} points plus sévère que vous.`}
            </p>
          )}
          {evaluation.commentaire && (
            <p className="text-[12px] text-txt2 italic">« {evaluation.commentaire} »</p>
          )}
          <p className="text-[11px] text-txt2 opacity-70">
            Évalué par {evaluation.evaluateur || "un recruteur"}
          </p>
        </div>
      )}

      {ouvert && (
        <div className="rounded-[10px] border border-bordure bg-surface2/40 p-3.5 space-y-3">
          <div className="space-y-2">
            {criteres.map((c) => (
              <div key={c.code} className="flex items-center justify-between gap-3">
                <span className="text-[12.5px] flex-1">{c.libelle}</span>
                <div className="flex gap-1 shrink-0">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() =>
                        setNotes((p) =>
                          p[c.code] === n
                            ? Object.fromEntries(
                                Object.entries(p).filter(([k]) => k !== c.code)
                              )
                            : { ...p, [c.code]: n }
                        )
                      }
                      aria-label={`${c.libelle} : ${n} sur 5`}
                      aria-pressed={notes[c.code] === n}
                      className={`w-7 h-7 rounded-[6px] text-[12px] font-semibold transition-colors ${
                        notes[c.code] >= n
                          ? "bg-accent text-white"
                          : "bg-fond border border-bordure text-txt2 hover:border-accent"
                      }`}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            <p className="text-[11px] text-txt2">
              Cliquez de nouveau sur une note pour l'effacer. Les critères non
              renseignés sont simplement ignorés.
            </p>
          </div>

          <div>
            <label htmlFor="verdict-entretien" className="etiquette">Verdict</label>
            <select
              id="verdict-entretien"
              className="champ text-[13px]"
              value={verdict}
              onChange={(e) => setVerdict(e.target.value)}
            >
              {verdicts.map((v) => (
                <option key={v.code} value={v.code}>{v.libelle}</option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="commentaire-entretien" className="etiquette">
              Commentaire <span className="font-normal">(facultatif)</span>
            </label>
            <textarea
              id="commentaire-entretien"
              className="champ text-[13px] min-h-[60px]"
              value={commentaire}
              onChange={(e) => setCommentaire(e.target.value)}
              placeholder="Points forts, réserves, suite à donner…"
            />
          </div>

          {erreur && <p className="text-[12px] text-erreur">{erreur}</p>}

          <div className="flex gap-2">
            <button
              onClick={enregistrer}
              disabled={envoi || renseignees === 0}
              className="btn-primaire text-[12.5px] py-1.5 px-3 min-h-0"
            >
              {envoi ? "Enregistrement…" : "Enregistrer"}
            </button>
            <button
              onClick={() => setOuvert(false)}
              className="btn-fantome text-[12.5px] py-1.5 px-3 min-h-0"
            >
              Annuler
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

const MOTIFS_MANUELS = [
  { cle: "identite_divergente", libelle: "Doute sur l'identité du candidat" },
  { cle: "diplome_douteux", libelle: "Diplôme ou établissement douteux" },
  { cle: "experience_invraisemblable", libelle: "Expérience invraisemblable" },
  { cle: "references_fausses", libelle: "Références introuvables ou fausses" },
  { cle: "document_similaire", libelle: "CV proche de celui d'un autre candidat" },
  { cle: "autre", libelle: "Autre anomalie" },
];

/**
 * Signalement ouvert à la main par le recruteur.
 *
 * Les contrôles automatiques ne voient que ce que le document contient. Un
 * recruteur peut téléphoner à un ancien employeur, reconnaître un diplôme qui
 * n'existe pas, ou constater en entretien que le candidat ne correspond pas à
 * son curriculum. Cette voie complète la machine plutôt qu'elle ne la double.
 */
function SignalerDossier({ candidature, onSignale }) {
  const [ouvert, setOuvert] = useState(false);
  const [motif, setMotif] = useState(MOTIFS_MANUELS[0].cle);
  const [severite, setSeverite] = useState("attention");
  const [message, setMessage] = useState("");
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState("");

  const envoyer = async () => {
    setEnvoi(true);
    setErreur("");
    try {
      await api.ouvrirSignalement(candidature.id, motif, message.trim(), severite);
      setOuvert(false);
      setMessage("");
      onSignale?.();
    } catch (e) {
      setErreur(e.message);
    } finally {
      setEnvoi(false);
    }
  };

  if (!ouvert) {
    return (
      <button
        onClick={() => setOuvert(true)}
        className="text-[12px] text-txt2 hover:text-alerte transition-colors inline-flex items-center gap-1.5"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
          <path d="M4 21V4h13l-1.5 4L17 12H4" />
        </svg>
        Signaler une anomalie sur ce dossier
      </button>
    );
  }

  return (
    <div className="rounded-[10px] border border-alerte/40 bg-alerte/5 p-3.5 space-y-2.5">
      <p className="text-xs font-semibold text-alerte">Signaler une anomalie</p>
      <p className="text-[11px] text-txt2 leading-snug">
        Votre observation sera enregistrée avec votre nom et transmise à
        l'administration. Elle ne modifie ni la note ni le statut de la
        candidature.
      </p>

      <div className="grid sm:grid-cols-2 gap-2">
        <div>
          <label htmlFor="motif-signalement" className="etiquette">Motif</label>
          <select
            id="motif-signalement"
            className="champ text-[13px]"
            value={motif}
            onChange={(e) => setMotif(e.target.value)}
          >
            {MOTIFS_MANUELS.map((m) => (
              <option key={m.cle} value={m.cle}>{m.libelle}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="severite-signalement" className="etiquette">Gravité</label>
          <select
            id="severite-signalement"
            className="champ text-[13px]"
            value={severite}
            onChange={(e) => setSeverite(e.target.value)}
          >
            <option value="information">Information</option>
            <option value="attention">Vigilance</option>
            <option value="alerte">Alerte</option>
          </select>
        </div>
      </div>

      <div>
        <label htmlFor="message-signalement" className="etiquette">
          Ce que vous avez constaté
        </label>
        <textarea
          id="message-signalement"
          className="champ text-[13px] min-h-[70px]"
          placeholder="L'entreprise citée pour 2021-2023 n'existe pas au registre du commerce."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
      </div>

      {erreur && <p className="text-[12px] text-erreur">{erreur}</p>}

      <div className="flex gap-2">
        <button
          onClick={envoyer}
          disabled={envoi || message.trim().length < 10}
          className="btn-primaire text-[12.5px] py-1.5 px-3 min-h-0"
        >
          {envoi ? "Enregistrement…" : "Enregistrer le signalement"}
        </button>
        <button
          onClick={() => setOuvert(false)}
          className="btn-fantome text-[12.5px] py-1.5 px-3 min-h-0"
        >
          Annuler
        </button>
      </div>
    </div>
  );
}

function DetailCandidature({ candidature, onStatut, onAnalyse }) {
  const d = candidature.score_details || {};
  const coul = couleurScore(candidature.score);
  const nonAnalysee = candidature.score == null;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-4">
        <JaugeScore score={candidature.score} taille={68} anime />
        <div>
          <p className={`text-2xl font-bold ${coul.texte} tabular-nums`}>
            {nonAnalysee ? "Non analysée" : <><CompteurScore valeur={candidature.score} />/100</>}
          </p>
          <p className="text-xs text-txt2">{candidature.offer?.title}</p>
        </div>
      </div>

      {/* Avertissement placé juste sous la note, avant tout le reste : un
          recruteur qui ne lirait qu'une chose doit lire celle-ci. */}
      <AvertissementControles signalements={candidature.signalements} />

      {/* Voie humaine : ce que les contrôles automatiques ne peuvent pas voir */}
      <SignalerDossier candidature={candidature} onSignale={onAnalyse} />

      <BlocAnalyse candidature={candidature} onAnalyse={onAnalyse} nonAnalysee={nonAnalysee} />

      {/* Motif de rejet par règle : exigence d'explicabilité */}
      {d.eliminatoires?.length > 0 && (
        <div className="rounded-[10px] border border-erreur/40 bg-erreur/10 p-3.5">
          <p className="text-xs font-semibold text-erreur mb-1.5">Critères éliminatoires non remplis</p>
          <ul className="space-y-1">
            {d.eliminatoires.map((m) => (
              <li key={m} className="text-[12.5px] text-txt2">• {m}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Écarts mesurés qui n'éliminent pas : le recruteur en juge lui-même */}
      {d.reserves?.length > 0 && (
        <div className="rounded-[10px] border border-alerte/40 bg-alerte/10 p-3.5">
          <p className="text-xs font-semibold text-alerte mb-1.5">
            Candidature retenue sous réserve
          </p>
          <ul className="space-y-1">
            {d.reserves.map((m) => (
              <li key={m} className="text-[12.5px] text-txt2">• {m}</li>
            ))}
          </ul>
        </div>
      )}

      {d.composantes && (
        <section>
          <h3 className="text-xs font-semibold text-txt2 mb-2.5">
            Détail du calcul
            <span className="font-normal"> — d'où vient le {candidature.score}</span>
          </h3>
          <div className="space-y-2.5">
            {/* Les composantes se révèlent dans l'ordre où elles s'additionnent :
                la décomposition se lit, elle ne se devine pas. */}
            {d.composantes.map((c, i) => (
              <div key={c.libelle} className="entree" style={{ animationDelay: retard(i, 70) }}>
                <div className="flex justify-between text-xs mb-1">
                  <span>{c.libelle}</span>
                  <span className="text-txt2 tabular-nums">{c.valeur}/{c.max}</span>
                </div>
                <div className="h-1.5 bg-fond rounded-full overflow-hidden">
                  <div
                    className="h-full bg-accent rounded-full jauge-remplissage"
                    style={{
                      width: `${(c.valeur / c.max) * 100}%`,
                      animationDelay: retard(i, 70),
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          {d.modele && (
            <div className="mt-3 rounded-xl2 border border-bordure bg-surface2/40 px-3 py-2.5">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-[11.5px] font-medium">Avis du modèle appris</span>
                <span className="text-[11.5px] text-txt2">
                  {Math.round(d.modele.probabilite * 100)} % de chances de convenir
                </span>
              </div>
              <p className="mt-1 text-[11px] text-txt2 leading-snug">
                {d.modele.applique ? (
                  <>
                    Note établie par les règles : {d.modele.score_avant_ajustement}
                    {" "}· ajustement {d.modele.ajustement > 0 ? "+" : "−"}
                    {Math.abs(d.modele.ajustement).toFixed(1).replace(".", ",")}
                    {" "}point{Math.abs(d.modele.ajustement) >= 2 ? "s" : ""}, borné à ±
                    {d.modele.amplitude_maximale}.
                  </>
                ) : (
                  d.modele.commentaire
                )}
              </p>
            </div>
          )}
        </section>
      )}

      {d.profil_ats ? (
        <ProfilAts profil={d.profil_ats} extraction={d.extraction} similarite={d.similarite} />
      ) : (
        d.profil_analyse && (
          <ProfilDetecte
            profil={d.profil_analyse}
            extraction={d.extraction}
            similarite={d.similarite}
          />
        )
      )}

      <section className="space-y-3">
        <CorrespondanceCompetences details={d} nonAnalysee={nonAnalysee} />

        {(d.competences_souhaitees_trouvees?.length > 0 ||
          d.competences_souhaitees_manquantes?.length > 0) && (
          <div>
            <h3 className="text-xs font-semibold text-txt2 mb-2">
              Compétences souhaitées <span className="font-normal">(non bloquantes)</span>
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {(d.competences_souhaitees_trouvees || []).map((s) => (
                <span key={s} className="chip bg-cyan/10 text-cyan">✓ {s}</span>
              ))}
              {(d.competences_souhaitees_manquantes || []).map((s) => (
                <span key={s} className="chip bg-bordure/50 text-txt2">○ {s}</span>
              ))}
            </div>
          </div>
        )}
      </section>

      <BoutonCV candidatureId={candidature.id} />

      <GrilleEntretien candidature={candidature} />

      <ImpressionFiche candidature={candidature} />

      <section className="border-t border-bordure pt-4">
        <h3 className="text-xs font-semibold text-txt2 mb-2.5">Décision</h3>
        <div className="grid grid-cols-2 gap-2">
          <button onClick={() => onStatut(candidature, "interview")} className="btn-primaire">Convoquer</button>
          <button onClick={() => onStatut(candidature, "hired")} className="btn-secondaire text-succes">Recruter</button>
          <button onClick={() => onStatut(candidature, "rejected")} className="btn-secondaire">Ne pas retenir</button>
          {(candidature.score ?? 0) < SEUIL_RETENU && (
            <button onClick={() => onStatut(candidature, "shortlisted")} className="btn-secondaire text-cyan">
              Repêcher
            </button>
          )}
        </div>
        <p className="text-[11px] text-txt2 mt-3 leading-snug">
          L'algorithme propose un classement ; la décision finale vous appartient.
        </p>
      </section>
    </div>
  );
}

const LIBELLE_EXTRACTION = {
  texte_natif: "Texte extrait directement du PDF",
  ocr: "Document scanné — lu par reconnaissance optique",
  echec: "Contenu illisible",
};

const LIBELLE_SIMILARITE = {
  plongements: "modèle sémantique",
  "tf-idf": "comparaison lexicale",
  indisponible: "non calculée",
};

const LIBELLE_METHODE = { texte_natif: "PDF", ocr: "OCR", docx: "DOCX", echec: "—" };

const moisEnDuree = (mois) => {
  const a = Math.floor(mois / 12);
  const m = mois % 12;
  if (a && m) return `${a} an${a > 1 ? "s" : ""} ${m} mois`;
  if (a) return `${a} an${a > 1 ? "s" : ""}`;
  return `${m} mois`;
};

const formatDate = (iso) => {
  if (!iso) return "présent";
  const [a, m] = iso.split("-");
  return `${m}/${a}`;
};

/**
 * Profil structuré issu du parsing ATS : identité, parcours, formations,
 * certifications et langues, tels que reconstitués depuis le CV.
 */
function ProfilAts({ profil, extraction, similarite }) {
  const b = profil.basics || {};

  return (
    <section className="rounded-xl2 border border-bordure bg-surface2/50 overflow-hidden">
      <header className="flex items-center justify-between gap-2 px-4 py-2.5 border-b border-bordure">
        <h3 className="text-xs font-semibold text-txt2">Profil extrait du CV</h3>
        <div className="flex items-center gap-1.5">
          {extraction && (
            <span className="chip bg-bordure/40 text-txt2 text-[10px]">
              {LIBELLE_METHODE[extraction.methode] || extraction.methode}
            </span>
          )}
          {profil.sectionsDetectees?.length > 0 && (
            <span
              className="chip bg-bordure/40 text-txt2 text-[10px]"
              title={profil.sectionsDetectees.join(", ")}
            >
              {profil.sectionsDetectees.length} sections
            </span>
          )}
        </div>
      </header>

      <div className="p-4 space-y-4">
        {/* Identité */}
        {(b.name || b.email || b.phone) && (
          <div>
            {b.name && <p className="font-semibold text-sm">{b.name}</p>}
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[11.5px] text-txt2 mt-0.5">
              {b.email && <span>{b.email}</span>}
              {b.phone && <span>{b.phone}</span>}
              {b.linkedin && <span>in/{b.linkedin}</span>}
            </div>
          </div>
        )}

        {/* Synthèse */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <Indicateur valeur={`${profil.totalExperienceYears} an(s)`} libelle="Expérience" />
          <Indicateur valeur={profil.highestDegree || "—"} libelle="Diplôme" />
          <Indicateur valeur={profil.skills?.length || 0} libelle="Compétences" />
        </div>

        {/* Parcours professionnel */}
        {profil.work?.length > 0 && (
          <div>
            <p className="text-[11px] text-txt2 font-medium mb-2">Parcours professionnel</p>
            <ol className="space-y-2.5">
              {profil.work.map((poste, i) => (
                <li key={i} className="flex gap-2.5">
                  <span className="w-1 rounded-full bg-accent/40 shrink-0 mt-1 mb-1" />
                  <div className="min-w-0">
                    <p className="text-[12.5px] font-medium leading-snug">
                      {poste.position || "Poste non identifié"}
                    </p>
                    <p className="text-[11.5px] text-txt2">
                      {poste.company && <span>{poste.company} · </span>}
                      {formatDate(poste.startDate)} → {formatDate(poste.endDate)}
                      {poste.months > 0 && <span> · {moisEnDuree(poste.months)}</span>}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Formation */}
        {profil.education?.length > 0 && (
          <div>
            <p className="text-[11px] text-txt2 font-medium mb-1.5">Formation</p>
            <ul className="space-y-1">
              {profil.education.map((f, i) => (
                <li key={i} className="text-[12px] flex gap-2">
                  {f.level && <span className="chip bg-accent/10 text-accent text-[10px] shrink-0">{f.level}</span>}
                  <span className="text-txt2 truncate">{f.studyType}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Certifications */}
        {profil.certificates?.length > 0 && (
          <div>
            <p className="text-[11px] text-txt2 font-medium mb-1.5">Certifications</p>
            <ul className="space-y-1">
              {profil.certificates.map((c, i) => (
                <li key={i} className="text-[12px] text-txt2">
                  {c.name}
                  {c.date && <span className="text-[11px]"> ({c.date})</span>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Langues */}
        {profil.languages?.length > 0 && (
          <div>
            <p className="text-[11px] text-txt2 font-medium mb-1.5">Langues</p>
            <div className="flex flex-wrap gap-1.5">
              {profil.languages.map((li) => (
                <span key={li.language} className="chip bg-bordure/40 text-txt2 text-[10px]">
                  {li.language}
                  {li.fluency && <span className="text-cyan ml-1">{li.fluency}</span>}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Compétences détectées */}
        {profil.skills?.length > 0 && (
          <div>
            <p className="text-[11px] text-txt2 font-medium mb-1.5">
              Compétences détectées ({profil.skills.length})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {profil.skills.slice(0, 14).map((s) => (
                <span key={s} className="chip bg-cyan/10 text-cyan text-[10px]">{s}</span>
              ))}
              {profil.skills.length > 14 && (
                <span className="chip bg-bordure/40 text-txt2 text-[10px]">
                  +{profil.skills.length - 14}
                </span>
              )}
            </div>
          </div>
        )}

        {similarite && (
          <p className="text-[11px] text-txt2 border-t border-bordure pt-2.5">
            Proximité sémantique avec l'offre : {Math.round(similarite.valeur * 100)} %
            <span className="opacity-70"> ({LIBELLE_SIMILARITE[similarite.methode] || similarite.methode})</span>
          </p>
        )}
      </div>
    </section>
  );
}

function Indicateur({ valeur, libelle }) {
  return (
    <div className="bg-fond rounded-[10px] py-2">
      <p className="text-sm font-semibold">{valeur}</p>
      <p className="text-[10.5px] text-txt2">{libelle}</p>
    </div>
  );
}

/** Restitue ce que le système a lu dans le CV : base de l'explicabilité. */
function ProfilDetecte({ profil, extraction, similarite }) {
  return (
    <section className="rounded-xl2 border border-bordure bg-surface2/50 p-4 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold text-txt2">Profil détecté dans le CV</h3>
        {extraction && (
          <span className="chip bg-bordure/40 text-txt2 text-[10px]">
            {extraction.methode === "ocr" ? "OCR" : "PDF"}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 text-[12.5px]">
        <div>
          <p className="text-txt2 text-[11px]">Expérience</p>
          <p className="font-medium">{profil.experience_years} an(s)</p>
        </div>
        <div>
          <p className="text-txt2 text-[11px]">Diplôme</p>
          <p className="font-medium">{profil.degree || "non détecté"}</p>
        </div>
      </div>

      {profil.skills?.length > 0 && (
        <div>
          <p className="text-txt2 text-[11px] mb-1.5">
            {profil.skills.length} compétence(s) repérée(s)
          </p>
          <div className="flex flex-wrap gap-1.5">
            {profil.skills.slice(0, 12).map((s) => (
              <span key={s} className="chip bg-cyan/10 text-cyan text-[10px]">{s}</span>
            ))}
            {profil.skills.length > 12 && (
              <span className="chip bg-bordure/40 text-txt2 text-[10px]">
                +{profil.skills.length - 12}
              </span>
            )}
          </div>
        </div>
      )}

      <p className="text-[11px] text-txt2 leading-snug border-t border-bordure pt-2.5">
        {extraction && (LIBELLE_EXTRACTION[extraction.methode] || "")}
        {similarite && (
          <> · Proximité avec l'offre : {Math.round(similarite.valeur * 100)} %
            ({LIBELLE_SIMILARITE[similarite.methode] || similarite.methode})</>
        )}
      </p>
    </section>
  );
}

/** Ouvre le CV dans un nouvel onglet en transmettant le jeton d'authentification. */
/**
 * Consultation du CV : affichage dans le panneau plutôt que téléchargement.
 *
 * Le document s'affiche à côté du profil reconstitué, ce qui permet de
 * vérifier d'un coup d'œil que l'extraction est fidèle — l'explicabilité ne
 * vaut que si le recruteur peut confronter ce que le système a lu à ce que le
 * document contient réellement. Le téléchargement reste offert : certains
 * préféreront leur propre lecteur, et un PDF protégé peut refuser de
 * s'afficher dans un cadre.
 */
function BoutonCV({ candidatureId }) {
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState("");
  const [url, setUrl] = useState(null);
  const [ouvert, setOuvert] = useState(false);

  // L'URL d'objet occupe la mémoire du navigateur tant qu'elle n'est pas
  // révoquée : la libérer au démontage évite une fuite au fil des ouvertures.
  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [url]);

  const basculer = async () => {
    if (ouvert) return setOuvert(false);
    if (url) return setOuvert(true);

    setChargement(true);
    setErreur("");
    try {
      setUrl(await telechargerFichier(`/applications/${candidatureId}/cv`));
      setOuvert(true);
    } catch (e) {
      setErreur(e.message);
    } finally {
      setChargement(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <button onClick={basculer} disabled={chargement} className="btn-secondaire flex-1">
          {chargement ? "Chargement…" : ouvert ? "Masquer le CV" : "Afficher le CV"}
        </button>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noreferrer"
            className="btn-fantome shrink-0"
            title="Ouvrir dans un onglet séparé"
          >
            ↗
          </a>
        )}
      </div>

      {erreur && <p className="text-xs text-erreur">{erreur}</p>}

      {ouvert && url && (
        <div className="rounded-[10px] border border-bordure overflow-hidden bg-fond">
          <object data={url} type="application/pdf" className="w-full h-[520px]">
            {/* Repli affiché lorsque le navigateur refuse d'intégrer le PDF */}
            <div className="p-5 text-center space-y-2">
              <p className="text-[13px] text-txt2">
                Votre navigateur n'affiche pas ce document dans la page.
              </p>
              <a href={url} target="_blank" rel="noreferrer" className="btn-secondaire inline-flex">
                Ouvrir dans un onglet
              </a>
            </div>
          </object>
        </div>
      )}
    </div>
  );
}

/**
 * Analyse d'une candidature : relecture automatique du CV en action
 * principale, saisie manuelle du profil en solution de secours lorsque le
 * document est illisible.
 */
function BlocAnalyse({ candidature, onAnalyse, nonAnalysee }) {
  const [enCours, setEnCours] = useState(false);
  const [manuel, setManuel] = useState(false);
  const [erreur, setErreur] = useState("");
  const statut = candidature.score_details?.statut;
  const echecLecture = ["extraction_echouee", "analyse_indisponible"].includes(statut);

  const relancer = async () => {
    setEnCours(true);
    setErreur("");
    try {
      const d = await api.analyser(candidature.id);
      onAnalyse(d.application);
    } catch (e) {
      setErreur(e.message);
    } finally {
      setEnCours(false);
    }
  };

  if (manuel) {
    return (
      <FormulaireAnalyse
        candidature={candidature}
        onAnalyse={(a) => { setManuel(false); onAnalyse(a); }}
        onAnnuler={() => setManuel(false)}
      />
    );
  }

  return (
    <section className="space-y-2">
      {echecLecture && (
        <div className="rounded-[10px] border border-alerte/40 bg-alerte/10 px-3.5 py-2.5">
          <p className="text-xs text-alerte font-semibold">Lecture automatique impossible</p>
          <p className="text-[11.5px] text-txt2 mt-1 leading-snug">
            {candidature.score_details?.message}
          </p>
        </div>
      )}

      <button onClick={relancer} disabled={enCours} className={nonAnalysee ? "btn-primaire w-full" : "btn-secondaire w-full text-cyan"}>
        {enCours ? "Analyse en cours…" : nonAnalysee ? "Analyser le CV" : "Relancer l'analyse"}
      </button>

      <button onClick={() => setManuel(true)} className="btn-fantome w-full text-[12px]">
        Saisir le profil manuellement
      </button>

      {erreur && <p className="text-xs text-erreur">{erreur}</p>}
    </section>
  );
}

/** Saisie manuelle du profil, en secours d'une lecture automatique impossible. */
function FormulaireAnalyse({ candidature, onAnalyse, onAnnuler }) {
  const profilPrecedent = candidature.score_details?.profil_analyse;
  const [competences, setCompetences] = useState(profilPrecedent?.skills || []);
  const [saisie, setSaisie] = useState("");
  const [experience, setExperience] = useState(profilPrecedent?.experience_years || 0);
  const [diplome, setDiplome] = useState(profilPrecedent?.degree || "");
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState("");

  const ajouter = (e) => {
    if (e.key !== "Enter" || !saisie.trim()) return;
    e.preventDefault();
    const v = saisie.trim().toLowerCase();
    if (!competences.includes(v)) setCompetences([...competences, v]);
    setSaisie("");
  };

  const lancer = async () => {
    setEnvoi(true);
    setErreur("");
    try {
      const d = await api.analyser(candidature.id, {
        skills: competences,
        experience_years: experience,
        degree: diplome || null,
      });
      onAnalyse(d.application);
    } catch (e) {
      setErreur(e.message);
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <section className="rounded-xl2 border border-accent/40 bg-accent/5 p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">Saisie manuelle du profil</h3>
          <p className="text-[11.5px] text-txt2 mt-1 leading-snug">
            À utiliser lorsque le document n'a pas pu être lu automatiquement.
            Renseignez ce que vous relevez dans le CV : le moteur calcule le score
            et son explication de la même manière.
          </p>
        </div>
        <button onClick={onAnnuler} aria-label="Annuler" className="text-txt2 hover:text-txt shrink-0">
          ×
        </button>
      </div>

      <div>
        <label htmlFor="comp-analyse" className="etiquette">Compétences (Entrée pour ajouter)</label>
        <input
          id="comp-analyse" className="champ" value={saisie}
          onChange={(e) => setSaisie(e.target.value)} onKeyDown={ajouter}
          placeholder="python, sql, docker…"
        />
        {competences.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {competences.map((c) => (
              <button
                key={c} type="button"
                onClick={() => setCompetences(competences.filter((x) => x !== c))}
                className="chip bg-accent/15 text-accent hover:bg-erreur/15 hover:text-erreur"
              >
                {c} ×
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2.5">
        <div>
          <label htmlFor="exp-analyse" className="etiquette">Expérience (années)</label>
          <input
            id="exp-analyse" type="number" min="0" max="40" className="champ"
            value={experience} onChange={(e) => setExperience(Number(e.target.value))}
          />
        </div>
        <div>
          <label htmlFor="dip-analyse" className="etiquette">Diplôme</label>
          <select id="dip-analyse" className="champ" value={diplome} onChange={(e) => setDiplome(e.target.value)}>
            <option value="">Non renseigné</option>
            <option value="Bac">Bac</option>
            <option value="Bac+2">Bac+2</option>
            <option value="Bac+3">Bac+3</option>
            <option value="Bac+5">Bac+5</option>
            <option value="Doctorat">Doctorat</option>
          </select>
        </div>
      </div>

      {erreur && <p className="text-xs text-erreur">{erreur}</p>}

      <button onClick={lancer} disabled={envoi} className="btn-primaire w-full">
        {envoi ? "Calcul en cours…" : "Calculer le score"}
      </button>
    </section>
  );
}
