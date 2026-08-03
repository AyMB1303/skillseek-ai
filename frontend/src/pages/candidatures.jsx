/** Candidatures classées : onglets RG-01, tri, drawer d'explicabilité, actions. */
import { useEffect, useState, useCallback, useMemo } from "react";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur, EtatVide, BadgeStatut, Drawer, useToast, STATUTS } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api, telechargerFichier } from "@/lib/api";
import { couleurScore, SEUIL_RETENU, PLAFOND_TOP } from "@/lib/scoring";

const ONGLETS = [
  { cle: "toutes", libelle: "Toutes" },
  { cle: "top", libelle: `Top ${PLAFOND_TOP} IA` },
  { cle: "ecartees", libelle: `Écartées (< ${SEUIL_RETENU})` },
  { cle: "attente", libelle: "Sans score" },
];

export default function Candidatures() {
  const { chargement: garde } = useGarde(["recruiter"]);
  const { notifier } = useToast();
  const [candidatures, setCandidatures] = useState([]);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");
  const [onglet, setOnglet] = useState("toutes");
  const [tri, setTri] = useState({ champ: "score", sens: "desc" });
  const [selection, setSelection] = useState(null);

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
    const analysees = candidatures.filter((c) => c.score != null);
    return {
      toutes: candidatures,
      top: [...analysees.filter((c) => c.score >= SEUIL_RETENU)]
        .sort((a, b) => b.score - a.score)
        .slice(0, PLAFOND_TOP),
      ecartees: analysees.filter((c) => c.score < SEUIL_RETENU),
      attente: candidatures.filter((c) => c.score == null),
    };
  }, [candidatures]);

  const affichees = useMemo(() => {
    return [...groupes[onglet]].sort((a, b) => {
      const va = tri.champ === "score" ? a.score ?? -1 : a.candidate?.full_name || "";
      const vb = tri.champ === "score" ? b.score ?? -1 : b.candidate?.full_name || "";
      const cmp = typeof va === "number" ? va - vb : String(va).localeCompare(String(vb));
      return tri.sens === "asc" ? cmp : -cmp;
    });
  }, [groupes, onglet, tri]);

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
                {affichees.map((c) => {
                  const coul = couleurScore(c.score);
                  const trouvees = c.score_details?.competences_trouvees || [];
                  const manquantes = c.score_details?.competences_manquantes || [];
                  return (
                    <tr key={c.id} className="border-b border-bordure last:border-0 hover:bg-surface2/60">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-bordure text-cyan grid place-items-center text-[11px] font-bold shrink-0">
                            {(c.candidate?.full_name || "?").split(" ").map((m) => m[0]).slice(0, 2).join("")}
                          </div>
                          <div className="min-w-0">
                            <div className="font-medium truncate">{c.candidate?.full_name}</div>
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

function JaugeScore({ score }) {
  const coul = couleurScore(score);
  const pct = score ?? 0;
  const r = 15;
  const circ = 2 * Math.PI * r;
  return (
    <div className="relative w-11 h-11 shrink-0" title={`Score : ${score ?? "non calculé"}/100`}>
      <svg viewBox="0 0 40 40" className="w-full h-full -rotate-90">
        <circle cx="20" cy="20" r={r} fill="none" stroke="#1E2A44" strokeWidth="4" />
        <circle
          cx="20" cy="20" r={r} fill="none" stroke={coul.anneau} strokeWidth="4" strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={circ - (pct / 100) * circ}
        />
      </svg>
      <span className={`absolute inset-0 grid place-items-center text-[11px] font-bold ${coul.texte}`}>
        {score ?? "—"}
      </span>
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
        <JaugeScore score={candidature.score} />
        <div>
          <p className={`text-2xl font-bold ${coul.texte}`}>
            {nonAnalysee ? "Non analysée" : `${candidature.score}/100`}
          </p>
          <p className="text-xs text-txt2">{candidature.offer?.title}</p>
        </div>
      </div>

      <BlocAnalyse candidature={candidature} onAnalyse={onAnalyse} nonAnalysee={nonAnalysee} />

      {/* Motif de rejet par règle : exigence d'explicabilité */}
      {d.eliminatoires?.length > 0 && (
        <div className="rounded-[10px] border border-alerte/40 bg-alerte/10 p-3.5">
          <p className="text-xs font-semibold text-alerte mb-1.5">Critères éliminatoires non remplis</p>
          <ul className="space-y-1">
            {d.eliminatoires.map((m) => (
              <li key={m} className="text-[12.5px] text-txt2">• {m}</li>
            ))}
          </ul>
        </div>
      )}

      {d.composantes && (
        <section>
          <h3 className="text-xs font-semibold text-txt2 mb-2.5">Détail du calcul</h3>
          <div className="space-y-2.5">
            {d.composantes.map((c) => (
              <div key={c.libelle}>
                <div className="flex justify-between text-xs mb-1">
                  <span>{c.libelle}</span>
                  <span className="text-txt2">{c.valeur}/{c.max}</span>
                </div>
                <div className="h-1.5 bg-fond rounded-full overflow-hidden">
                  <div className="h-full bg-accent rounded-full" style={{ width: `${(c.valeur / c.max) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
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
        <div>
          <h3 className="text-xs font-semibold text-txt2 mb-2">Compétences obligatoires</h3>
          <div className="flex flex-wrap gap-1.5">
            {(d.competences_trouvees || []).map((s) => (
              <span key={s} className="chip bg-succes/10 text-succes">✓ {s}</span>
            ))}
            {(d.competences_manquantes || []).map((s) => (
              <span key={s} className="chip bg-erreur/10 text-erreur">✗ {s}</span>
            ))}
            {!d.competences_trouvees?.length && !d.competences_manquantes?.length && (
              <p className="text-xs text-txt2">
                {nonAnalysee
                  ? "Lancez l'analyse ci-dessus pour obtenir le détail des compétences."
                  : "Aucune compétence obligatoire n'était définie sur cette offre."}
              </p>
            )}
          </div>
        </div>

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
function BoutonCV({ candidatureId }) {
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState("");

  const ouvrir = async () => {
    setChargement(true);
    setErreur("");
    try {
      const url = await telechargerFichier(`/applications/${candidatureId}/cv`);
      window.open(url, "_blank");
      // Libère la mémoire une fois l'onglet ouvert.
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      setErreur(e.message);
    } finally {
      setChargement(false);
    }
  };

  return (
    <div>
      <button onClick={ouvrir} disabled={chargement} className="btn-secondaire w-full">
        {chargement ? "Ouverture…" : "Consulter le CV (PDF)"}
      </button>
      {erreur && <p className="text-xs text-erreur mt-1.5">{erreur}</p>}
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
