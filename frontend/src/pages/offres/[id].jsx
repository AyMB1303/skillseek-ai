/** Détail d'une offre + dépôt du CV (validation stricte du fichier). */
import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur, BadgeStatut, useToast } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";

const TAILLE_MAX = 5 * 1024 * 1024;

export default function DetailOffre() {
  const router = useRouter();
  const { id } = router.query;
  const { utilisateur, chargement: garde } = useGarde(["candidate", "recruiter", "admin"]);
  const { notifier } = useToast();

  const [offre, setOffre] = useState(null);
  const [maCandidature, setMaCandidature] = useState(null);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");

  const [fichier, setFichier] = useState(null);
  const [erreurFichier, setErreurFichier] = useState("");
  const [survol, setSurvol] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const champFichier = useRef(null);

  const charger = useCallback(async () => {
    if (!id) return;
    setEtat("chargement");
    try {
      const d = await api.offre(id);
      setOffre(d.offer);
      if (utilisateur?.role === "candidate") {
        const mes = await api.mesCandidatures();
        setMaCandidature(mes.applications.find((c) => c.offer?.id === Number(id)) || null);
      }
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
    }
  }, [id, utilisateur]);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  /** Validation locale avant envoi : format et taille. */
  const choisirFichier = (f) => {
    setErreurFichier("");
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setErreurFichier("Format non accepté : seuls les fichiers PDF sont autorisés.");
      setFichier(null);
      return;
    }
    if (f.size > TAILLE_MAX) {
      setErreurFichier("Fichier trop volumineux (5 Mo maximum).");
      setFichier(null);
      return;
    }
    setFichier(f);
  };

  const postuler = async () => {
    if (!fichier) {
      setErreurFichier("Veuillez sélectionner votre CV au format PDF.");
      return;
    }
    setEnvoi(true);
    try {
      const d = await api.postuler(Number(id), fichier);
      setMaCandidature({ id: d.application.id, status: d.application.status, offer: { id: Number(id) } });
      setFichier(null);
      notifier("Candidature envoyée. Vous pouvez suivre son avancement.");
    } catch (e) {
      setErreurFichier(e.message);
    } finally {
      setEnvoi(false);
    }
  };

  if (garde) return null;

  return (
    <Layout titre="Détail de l'offre">
      <nav className="text-xs text-txt2 mb-4" aria-label="Fil d'Ariane">
        <Link href="/offres" className="hover:text-txt">Offres d'emploi</Link>
        <span className="mx-1.5">/</span>
        <span className="text-txt">{offre?.title || "…"}</span>
      </nav>

      {etat === "chargement" && <Chargement lignes={3} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" && offre && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 space-y-5">
            <section className="carte p-6">
              <h1 className="text-xl font-bold">{offre.title}</h1>
              <p className="text-xs text-txt2 mt-1.5">
                Publiée le {new Date(offre.created_at).toLocaleDateString("fr-FR")}
              </p>

              <div className="flex flex-wrap gap-1.5 mt-4">
                {(offre.required_skills || []).map((s) => (
                  <span key={s} className="chip bg-accent/10 text-accent">{s}</span>
                ))}
              </div>

              <p className="text-sm leading-relaxed text-txt2 mt-5 whitespace-pre-line">{offre.description}</p>
            </section>

            <section className="carte p-6">
              <h2 className="font-semibold text-sm mb-3">Critères requis</h2>
              <ul className="space-y-2">
                <Critere
                  libelle={
                    offre.min_experience_years
                      ? `${offre.min_experience_years} an(s) d'expérience minimum`
                      : "Aucune expérience minimale exigée"
                  }
                />
                <Critere libelle={offre.min_degree ? `Diplôme ${offre.min_degree} minimum` : "Aucun diplôme exigé"} />
                {(offre.required_skills || []).length > 0 && (
                  <Critere libelle={`Compétences : ${offre.required_skills.join(", ")}`} />
                )}
              </ul>
              <p className="text-[11px] text-txt2 mt-3 leading-snug">
                Les deux premiers critères sont éliminatoires : votre candidature sera écartée du classement
                si vous ne les remplissez pas, mais elle restera consultable par le recruteur.
              </p>
            </section>
          </div>

          {/* ---------- Zone de candidature ---------- */}
          <aside className="lg:sticky lg:top-24 h-fit">
            {utilisateur?.role !== "candidate" ? (
              <div className="carte p-5">
                <p className="text-sm text-txt2">
                  Seuls les comptes candidats peuvent postuler.
                </p>
                {utilisateur?.role === "recruiter" && (
                  <Link href={`/candidatures?offre=${offre.id}`} className="btn-secondaire w-full mt-3">
                    Voir les candidatures
                  </Link>
                )}
              </div>
            ) : maCandidature ? (
              <div className="carte p-5 space-y-3">
                <p className="text-sm">Vous avez déjà postulé à cette offre.</p>
                <BadgeStatut statut={maCandidature.status} />
                <Link href="/mes-candidatures" className="btn-secondaire w-full">Suivre ma candidature</Link>
              </div>
            ) : (
              <div className="carte p-5 space-y-3">
                <h2 className="font-semibold text-sm">Postuler à cette offre</h2>

                <div
                  onDragOver={(e) => { e.preventDefault(); setSurvol(true); }}
                  onDragLeave={() => setSurvol(false)}
                  onDrop={(e) => { e.preventDefault(); setSurvol(false); choisirFichier(e.dataTransfer.files[0]); }}
                  onClick={() => champFichier.current?.click()}
                  onKeyDown={(e) => e.key === "Enter" && champFichier.current?.click()}
                  role="button"
                  tabIndex={0}
                  className={`rounded-xl2 border-2 border-dashed p-6 text-center cursor-pointer transition-colors ${
                    survol ? "border-accent bg-accent/5" : erreurFichier ? "border-erreur" : "border-bordure hover:border-accent"
                  }`}
                >
                  <input
                    ref={champFichier}
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    onChange={(e) => choisirFichier(e.target.files[0])}
                  />
                  {fichier ? (
                    <div>
                      <p className="text-sm font-medium truncate">{fichier.name}</p>
                      <p className="text-xs text-txt2 mt-1">{(fichier.size / 1024).toFixed(0)} Ko</p>
                      <button
                        onClick={(e) => { e.stopPropagation(); setFichier(null); }}
                        className="text-xs text-erreur hover:underline mt-2"
                      >
                        Retirer
                      </button>
                    </div>
                  ) : (
                    <>
                      <p className="text-sm">Déposez votre CV ici</p>
                      <p className="text-xs text-txt2 mt-1">PDF uniquement · 5 Mo maximum</p>
                    </>
                  )}
                </div>

                {erreurFichier && <p role="alert" className="text-xs text-erreur">{erreurFichier}</p>}

                <button onClick={postuler} disabled={envoi || !fichier} className="btn-primaire w-full">
                  {envoi ? "Envoi en cours…" : "Envoyer ma candidature"}
                </button>

                <p className="text-[11px] text-txt2 leading-snug">
                  Votre CV sera analysé automatiquement pour évaluer sa correspondance avec l'offre.
                  La décision finale est prise par un recruteur.
                </p>
              </div>
            )}
          </aside>
        </div>
      )}
    </Layout>
  );
}

function Critere({ libelle }) {
  return (
    <li className="flex items-start gap-2.5 text-sm">
      <span className="text-accent mt-0.5">•</span>
      <span className="text-txt2">{libelle}</span>
    </li>
  );
}
