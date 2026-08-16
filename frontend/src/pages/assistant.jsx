/** Assistant conversationnel : questions en langage naturel sur les recrutements. */
import { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";

const LIBELLE_RECHERCHE = {
  plongements: "recherche sémantique",
  lexicale: "recherche lexicale",
};

const LIBELLE_GENERATION = {
  ollama: "modèle local",
  api: "modèle distant",
  gabarits: "réponses calculées",
  conversation: "réponses calculées",
};

const LIBELLE_SOURCE = {
  aide: "Aide",
  offre: "Offre",
  candidature: "Candidature",
  compte: "Compte",
  signalement: "Signalement",
  role: "Rôle",
};

// L'assistant sert deux métiers distincts. L'administrateur n'interroge pas
// les candidatures — son rôle ne détient pas ce droit — mais les comptes, les
// permissions, les signalements et le journal. L'accueil doit le dire, sans
// quoi il poserait les questions d'un recruteur et n'obtiendrait rien.
const ACCUEIL = {
  recrutement: {
    titre: "Posez-moi une question sur vos recrutements",
    texte:
      "Je recherche l'information dans vos offres, vos candidatures et la " +
      "documentation de la plateforme, puis je vous réponds en citant mes sources.",
  },
  administration: {
    titre: "Posez-moi une question sur la plateforme",
    texte:
      "Comptes et demandes en attente, rôles et permissions, signalements, " +
      "journal d'audit et corbeille : je réponds en citant mes sources. Le " +
      "contenu des dossiers de candidature relève de l'espace du recruteur.",
  },
};

export default function Assistant() {
  const { chargement: garde } = useGarde(["recruiter", "admin"]);
  const [etat, setEtat] = useState(null);
  const [chargementEtat, setChargementEtat] = useState(true);
  const [erreurInitiale, setErreurInitiale] = useState("");
  const [messages, setMessages] = useState([]);
  const [saisie, setSaisie] = useState("");
  const [enCours, setEnCours] = useState(false);
  const finRef = useRef(null);

  const charger = useCallback(async () => {
    setChargementEtat(true);
    try {
      setEtat(await api.etatAssistant());
      setErreurInitiale("");
    } catch (e) {
      setErreurInitiale(e.message);
    } finally {
      setChargementEtat(false);
    }
  }, []);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, enCours]);

  const envoyer = async (texte) => {
    const question = (texte ?? saisie).trim();
    if (!question || enCours) return;

    const historique = messages
      .filter((m) => !m.erreur)
      .slice(-8)
      .map((m) => ({ role: m.role, texte: m.texte }));

    setMessages((m) => [...m, { role: "user", texte: question }]);
    setSaisie("");
    setEnCours(true);

    try {
      const reponse = await api.demanderAssistant(question, historique);
      setMessages((m) => [...m, { role: "assistant", ...reponse }]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", texte: e.message, erreur: true },
      ]);
    } finally {
      setEnCours(false);
    }
  };

  if (garde) return null;

  const accueil = ACCUEIL[etat?.domaine] || ACCUEIL.recrutement;

  return (
    <Layout titre={etat?.domaine === "administration" ? "Assistant" : "Assistant RH"}>
      {chargementEtat && <Chargement lignes={3} />}
      {erreurInitiale && <EtatErreur message={erreurInitiale} onReessayer={charger} />}

      {etat && (
        <div className="carte flex flex-col h-[calc(100vh-190px)] overflow-hidden">
          {/* Transparence sur le dispositif employé */}
          <div className="px-5 py-2.5 border-b border-bordure bg-surface2/50 flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11.5px] text-txt2">
              {etat.documents_indexes} document(s) indexé(s) ·{" "}
              {LIBELLE_RECHERCHE[etat.methode_recherche] || etat.methode_recherche} ·{" "}
              {LIBELLE_GENERATION[etat.fournisseur_generation] || etat.fournisseur_generation}
            </p>
            {messages.length > 0 && (
              <button
                onClick={() => setMessages([])}
                className="text-xs text-txt2 hover:text-txt shrink-0"
              >
                Nouvelle conversation
              </button>
            )}
          </div>

          {/* Fil de discussion */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-8">
                <div className="w-12 h-12 mx-auto rounded-xl2 bg-gradient-to-br from-accent to-cyan grid place-items-center mb-3">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0B1220"
                    strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
                    <path d="M21 12a8 8 0 0 1-8 8H4l2-3a8 8 0 1 1 15-5z" />
                  </svg>
                </div>
                <h2 className="font-semibold">{accueil.titre}</h2>
                <p className="text-sm text-txt2 mt-1.5 max-w-md mx-auto">
                  {accueil.texte}
                </p>
              </div>
            )}

            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="flex justify-end">
                  <p className="bg-accent text-white rounded-xl2 rounded-br-sm px-4 py-2.5 text-sm max-w-[75%]">
                    {m.texte}
                  </p>
                </div>
              ) : (
                <div key={i} className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent to-cyan grid place-items-center shrink-0 mt-0.5">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#0B1220"
                      strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
                      <path d="M12 3l1.4 3.6L17 8l-3.6 1.4L12 13l-1.4-3.6L7 8l3.6-1.4z" />
                    </svg>
                  </div>

                  <div
                    className={`rounded-xl2 rounded-tl-sm px-4 py-3 max-w-[85%] space-y-3 border ${
                      m.erreur
                        ? "bg-erreur/10 border-erreur/40"
                        : "bg-surface2 border-bordure"
                    }`}
                  >
                    <p className={`text-sm leading-relaxed whitespace-pre-line ${m.erreur ? "text-erreur" : ""}`}>
                      {m.texte}
                    </p>

                    {m.tableau && (
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="text-left text-txt2 border-b border-bordure">
                              {m.tableau.colonnes.map((c) => (
                                <th key={c} className="py-1.5 pr-4 font-medium whitespace-nowrap">{c}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {m.tableau.lignes.map((ligne, j) => (
                              <tr key={j} className="border-b border-bordure/50 last:border-0">
                                {ligne.map((cell, k) => (
                                  <td key={k} className="py-1.5 pr-4">{cell}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {m.lien && (
                      <Link href={m.lien.href} className="inline-block text-xs text-accent hover:text-cyan">
                        {m.lien.libelle} →
                      </Link>
                    )}

                    {/* Relances : la conversation se poursuit sans tout retaper */}
                    {m.suggestions?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {m.suggestions.map((s) => (
                          <button
                            key={s}
                            onClick={() => envoyer(s)}
                            className="chip bg-bordure/40 text-txt2 text-[11px] hover:bg-accent/15 hover:text-accent transition-colors"
                          >
                            {s}
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Sources : l'utilisateur peut vérifier d'où vient la réponse */}
                    {m.sources?.length > 0 && (
                      <details className="border-t border-bordure pt-2">
                        <summary className="text-[11px] text-txt2 cursor-pointer hover:text-txt">
                          {m.sources.length} source(s) consultée(s)
                        </summary>
                        <ul className="mt-2 space-y-1">
                          {m.sources.map((s) => (
                            <li key={s.id} className="text-[11px] text-txt2 flex items-center gap-2">
                              <span className="chip bg-bordure/40 text-txt2 text-[9.5px] shrink-0">
                                {LIBELLE_SOURCE[s.type] || s.type}
                              </span>
                              {s.lien ? (
                                <Link href={s.lien} className="hover:text-accent truncate">{s.titre}</Link>
                              ) : (
                                <span className="truncate">{s.titre}</span>
                              )}
                              <span className="ml-auto shrink-0 opacity-60">
                                {Math.round(s.pertinence * 100)} %
                              </span>
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                </div>
              )
            )}

            {enCours && (
              <div className="flex gap-3 items-center">
                <div className="w-8 h-8 rounded-full bg-bordure shrink-0" />
                <div className="flex gap-1 px-4 py-3" aria-label="Recherche en cours">
                  {[0, 150, 300].map((d) => (
                    <span key={d} className="w-1.5 h-1.5 rounded-full bg-txt2 animate-pulse"
                      style={{ animationDelay: `${d}ms` }} />
                  ))}
                </div>
              </div>
            )}
            <div ref={finRef} />
          </div>

          {/* Suggestions et saisie */}
          <div className="border-t border-bordure p-4 space-y-3">
            {messages.length === 0 && (
              <div className="flex flex-wrap gap-2">
                {(etat.suggestions || []).map((s) => (
                  <button
                    key={s}
                    onClick={() => envoyer(s)}
                    className="text-xs bg-surface2 border border-bordure rounded-full px-3.5 py-2 text-txt hover:border-cyan hover:text-cyan transition-colors"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            <form onSubmit={(e) => { e.preventDefault(); envoyer(); }} className="flex gap-2">
              <input
                className="champ flex-1"
                placeholder="Posez votre question…"
                value={saisie}
                onChange={(e) => setSaisie(e.target.value)}
                disabled={enCours}
                maxLength={500}
                aria-label="Question à l'assistant"
              />
              <button type="submit" disabled={!saisie.trim() || enCours} className="btn-primaire px-5">
                Envoyer
              </button>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
}
