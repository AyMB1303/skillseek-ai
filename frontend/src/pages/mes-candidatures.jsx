/** Suivi des candidatures du candidat : stepper de statut, sans score affiché. */
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur, EtatVide } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";
import { retard } from "@/lib/mouvement";

// Parcours visible par le candidat (le score IA reste interne au recruteur).
const ETAPES = ["Reçue", "En cours d'étude", "Entretien", "Décision"];

const INDEX_ETAPE = {
  received: 0,
  under_review: 1,
  shortlisted: 1,
  interview: 2,
  hired: 3,
  rejected: 3,
};

export default function MesCandidatures() {
  const { chargement: garde } = useGarde(["candidate"]);
  const [candidatures, setCandidatures] = useState([]);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      const d = await api.mesCandidatures();
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

  if (garde) return null;

  return (
    <Layout titre="Mes candidatures">
      {etat === "chargement" && <Chargement lignes={3} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" &&
        (candidatures.length === 0 ? (
          <EtatVide
            titre="Vous n'avez pas encore postulé"
            description="Parcourez les offres disponibles et déposez votre CV en quelques clics."
            action={<Link href="/offres" className="btn-primaire mt-2">Voir les offres</Link>}
          />
        ) : (
          <div className="space-y-4">
            {candidatures.map((c, rang) => {
              const index = INDEX_ETAPE[c.status] ?? 0;
              const refusee = c.status === "rejected";
              const recrutee = c.status === "hired";

              return (
                <article
                  key={c.id}
                  className="carte carte-reactive p-5 entree"
                  style={{ animationDelay: retard(rang, 70) }}
                >
                  <div className="flex items-start justify-between gap-4 mb-5">
                    <div>
                      <h2 className="font-semibold">{c.offer?.title}</h2>
                      <p className="text-xs text-txt2 mt-1">
                        Candidature déposée le {new Date(c.created_at).toLocaleDateString("fr-FR")}
                      </p>
                    </div>
                    {c.offer && (
                      <Link href={`/offres/${c.offer.id}`} className="text-xs text-accent hover:text-cyan shrink-0">
                        Voir l'offre
                      </Link>
                    )}
                  </div>

                  {/* Stepper horizontal */}
                  <ol className="flex items-center gap-1" aria-label="Avancement de la candidature">
                    {ETAPES.map((etape, i) => {
                      const atteinte = i <= index;
                      const derniere = i === ETAPES.length - 1;
                      const couleur = derniere && atteinte
                        ? recrutee ? "bg-succes" : refusee ? "bg-bordure" : "bg-accent"
                        : atteinte ? "bg-accent" : "bg-bordure";

                      return (
                        <li key={etape} className="flex-1 flex items-center gap-1">
                          <div className="flex-1">
                            <div className={`h-1.5 rounded-full ${couleur} transition-colors`} />
                            <p className={`text-[11.5px] mt-1.5 ${atteinte ? "text-txt" : "text-txt2"}`}>
                              {derniere && atteinte
                                ? recrutee ? "Acceptée" : refusee ? "Non retenue" : "Décision"
                                : etape}
                            </p>
                          </div>
                        </li>
                      );
                    })}
                  </ol>

                  {/* Retour factuel en cas de refus : la note reste interne,
                      mais un refus muet serait indéfendable — une décision
                      prise avec l'aide d'un traitement automatisé doit pouvoir
                      s'expliquer à la personne concernée. */}
                  {c.retour && (
                    <div className="mt-5 rounded-[10px] border border-bordure bg-surface2/50 p-3.5 space-y-2">
                      <p className="text-[13px] leading-relaxed">{c.retour.message}</p>

                      {c.retour.points.length > 0 && (
                        <ul className="space-y-1">
                          {c.retour.points.map((p) => (
                            <li key={p} className="text-[12.5px] text-txt2">• {p}</li>
                          ))}
                        </ul>
                      )}

                      {c.retour.avertissement && (
                        <p className="text-[11px] text-txt2 border-t border-bordure pt-2 leading-snug">
                          {c.retour.avertissement}
                        </p>
                      )}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        ))}
    </Layout>
  );
}
