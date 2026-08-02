/** Suivi des candidatures du candidat : stepper de statut, sans score affiché. */
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur, EtatVide } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";

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
            {candidatures.map((c) => {
              const index = INDEX_ETAPE[c.status] ?? 0;
              const refusee = c.status === "rejected";
              const recrutee = c.status === "hired";

              return (
                <article key={c.id} className="carte p-5">
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
                </article>
              );
            })}
          </div>
        ))}
    </Layout>
  );
}
