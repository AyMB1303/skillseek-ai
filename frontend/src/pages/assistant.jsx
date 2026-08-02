/** Assistant RH : interroge les vraies données et calcule ses réponses. */
import { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";
import { repondre, SUGGESTIONS } from "@/lib/assistant";

export default function Assistant() {
  const { chargement: garde } = useGarde(["recruiter"]);
  const [donnees, setDonnees] = useState(null);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");
  const [messages, setMessages] = useState([]);
  const [saisie, setSaisie] = useState("");
  const [ecrit, setEcrit] = useState(false);
  const finRef = useRef(null);

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      const [o, c] = await Promise.all([api.offres(), api.candidatures()]);
      setDonnees({ offres: o.offers, candidatures: c.applications });
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
    }
  }, []);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, ecrit]);

  const envoyer = (texte) => {
    const q = (texte ?? saisie).trim();
    if (!q || !donnees) return;

    setMessages((m) => [...m, { role: "user", texte: q }]);
    setSaisie("");
    setEcrit(true);

    // Court délai : rend la lecture plus naturelle, la réponse est déjà calculée.
    setTimeout(() => {
      setMessages((m) => [...m, { role: "assistant", ...repondre(q, donnees) }]);
      setEcrit(false);
    }, 450);
  };

  if (garde) return null;

  return (
    <Layout titre="Assistant RH" compteurCandidatures={donnees?.candidatures.length}>
      {etat === "chargement" && <Chargement lignes={3} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" && (
        <div className="carte flex flex-col h-[calc(100vh-190px)] overflow-hidden">
          {/* Bandeau de transparence */}
          <div className="px-5 py-2.5 border-b border-bordure bg-surface2/50 flex items-center justify-between gap-3">
            <p className="text-[11.5px] text-txt2">
              Les réponses sont calculées à partir de vos {donnees.candidatures.length} candidature(s)
              et {donnees.offres.length} offre(s).
            </p>
            {messages.length > 0 && (
              <button onClick={() => setMessages([])} className="text-xs text-txt2 hover:text-txt shrink-0">
                Nouvelle conversation
              </button>
            )}
          </div>

          {/* Fil de discussion */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-8">
                <div className="w-12 h-12 mx-auto rounded-xl2 bg-gradient-to-br from-accent to-cyan grid place-items-center mb-3">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0B1220" strokeWidth="2.2" strokeLinecap="round">
                    <path d="M21 12a8 8 0 0 1-8 8H4l2-3a8 8 0 1 1 15-5z" />
                  </svg>
                </div>
                <h2 className="font-semibold">Posez-moi une question sur vos recrutements</h2>
                <p className="text-sm text-txt2 mt-1.5 max-w-md mx-auto">
                  J'analyse vos offres et vos candidatures pour vous répondre en français courant.
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
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#0B1220" strokeWidth="2.4" strokeLinecap="round">
                      <path d="M12 3l1.4 3.6L17 8l-3.6 1.4L12 13l-1.4-3.6L7 8l3.6-1.4z" />
                    </svg>
                  </div>
                  <div className="bg-surface2 border border-bordure rounded-xl2 rounded-tl-sm px-4 py-3 max-w-[85%] space-y-3">
                    <p className="text-sm leading-relaxed">{m.texte}</p>

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
                                  <td key={k} className="py-1.5 pr-4 whitespace-nowrap">{cell}</td>
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
                  </div>
                </div>
              )
            )}

            {ecrit && (
              <div className="flex gap-3 items-center">
                <div className="w-8 h-8 rounded-full bg-bordure shrink-0" />
                <div className="flex gap-1 px-4 py-3">
                  {[0, 150, 300].map((d) => (
                    <span key={d} className="w-1.5 h-1.5 rounded-full bg-txt2 animate-pulse" style={{ animationDelay: `${d}ms` }} />
                  ))}
                </div>
              </div>
            )}
            <div ref={finRef} />
          </div>

          {/* Suggestions + saisie */}
          <div className="border-t border-bordure p-4 space-y-3">
            {messages.length === 0 && (
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((s) => (
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

            <form
              onSubmit={(e) => { e.preventDefault(); envoyer(); }}
              className="flex gap-2"
            >
              <input
                className="champ flex-1"
                placeholder="Posez votre question…"
                value={saisie}
                onChange={(e) => setSaisie(e.target.value)}
                aria-label="Question à l'assistant"
              />
              <button type="submit" disabled={!saisie.trim()} className="btn-primaire px-5">
                Envoyer
              </button>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
}
