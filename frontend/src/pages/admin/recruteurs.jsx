/** Validation des demandes de comptes recruteurs. */
import { useEffect, useState, useCallback } from "react";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur, EtatVide, Modale, useToast } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";

export default function AdminRecruteurs() {
  const { chargement: garde } = useGarde(["admin"]);
  const { notifier } = useToast();

  const [demandes, setDemandes] = useState([]);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");
  const [aRefuser, setARefuser] = useState(null);
  const [motif, setMotif] = useState("");
  const [enCours, setEnCours] = useState(null);

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      const d = await api.demandesEnAttente();
      setDemandes(d.users);
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
    }
  }, []);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  const approuver = async (demande) => {
    setEnCours(demande.id);
    try {
      await api.approuverCompte(demande.id);
      setDemandes((l) => l.filter((d) => d.id !== demande.id));
      notifier(`${demande.full_name} peut désormais se connecter.`);
    } catch (e) {
      notifier(e.message, { type: "erreur" });
    } finally {
      setEnCours(null);
    }
  };

  const refuser = async () => {
    try {
      await api.refuserCompte(aRefuser.id, motif.trim());
      setDemandes((l) => l.filter((d) => d.id !== aRefuser.id));
      notifier("Demande refusée.");
    } catch (e) {
      notifier(e.message, { type: "erreur" });
    } finally {
      setARefuser(null);
      setMotif("");
    }
  };

  if (garde) return null;

  return (
    <Layout titre="Demandes de comptes recruteurs">
      <p className="text-sm text-txt2 mb-5 max-w-2xl">
        Un recruteur publie des offres au nom de son entreprise. Chaque demande est donc
        soumise à votre validation avant que le compte ne devienne actif.
      </p>

      {etat === "chargement" && <Chargement lignes={3} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" &&
        (demandes.length === 0 ? (
          <EtatVide
            titre="Aucune demande en attente"
            description="Les nouvelles demandes de comptes recruteurs apparaîtront ici."
          />
        ) : (
          <div className="space-y-3">
            {demandes.map((d) => (
              <article key={d.id} className="carte p-5 flex flex-wrap items-start gap-4">
                <div className="w-11 h-11 rounded-full bg-alerte/15 text-alerte grid place-items-center text-sm font-bold shrink-0">
                  {d.full_name.split(" ").map((m) => m[0]).slice(0, 2).join("").toUpperCase()}
                </div>

                <div className="flex-1 min-w-[220px]">
                  <p className="font-semibold">{d.full_name}</p>
                  <p className="text-[13px] text-txt2">{d.email}</p>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[12.5px]">
                    <span>
                      <span className="text-txt2">Entreprise : </span>
                      <span className="font-medium">{d.company || "non renseignée"}</span>
                    </span>
                    {d.phone && (
                      <span>
                        <span className="text-txt2">Téléphone : </span>
                        <span className="font-medium">{d.phone}</span>
                      </span>
                    )}
                    <span className="text-txt2">
                      Demande du {new Date(d.created_at).toLocaleDateString("fr-FR")}
                    </span>
                  </div>

                  <Qualification qualification={d.qualification} />
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => approuver(d)}
                    disabled={enCours === d.id}
                    className="btn-primaire"
                  >
                    {enCours === d.id ? "Validation…" : "Valider"}
                  </button>
                  <button onClick={() => setARefuser(d)} className="btn-secondaire text-erreur">
                    Refuser
                  </button>
                </div>
              </article>
            ))}
          </div>
        ))}

      <Modale
        ouverte={!!aRefuser}
        onFermer={() => { setARefuser(null); setMotif(""); }}
        titre="Refuser la demande"
        actions={
          <>
            <button onClick={() => { setARefuser(null); setMotif(""); }} className="btn-fantome">
              Annuler
            </button>
            <button onClick={refuser} className="btn bg-erreur text-white hover:opacity-90">
              Confirmer le refus
            </button>
          </>
        }
      >
        <p className="text-sm mb-4">
          Refuser la demande de <strong>{aRefuser?.full_name}</strong>
          {aRefuser?.company && <> pour {aRefuser.company}</>} ?
        </p>
        <label htmlFor="motif" className="etiquette">Motif communiqué au demandeur (facultatif)</label>
        <textarea
          id="motif" rows={3} className="champ resize-none"
          value={motif} onChange={(e) => setMotif(e.target.value)}
          placeholder="Entreprise non vérifiable, informations incomplètes…"
        />
        <p className="text-[11px] text-txt2 mt-2">
          Le motif est transmis au demandeur, qui le verra lors de sa prochaine tentative
          de connexion.
        </p>
      </Modale>
    </Layout>
  );
}

const STYLE_GRAVITE = {
  alerte: "border-erreur/40 bg-erreur/8",
  attention: "border-alerte/40 bg-alerte/8",
  information: "border-bordure bg-surface2/50",
};

const COULEUR_GRAVITE = {
  alerte: "text-erreur",
  attention: "text-alerte",
  information: "text-txt2",
};

/**
 * Faisceau d'indices sur une demande de compte recruteur.
 *
 * Publier une offre engage l'entreprise représentée : la validation par un
 * administrateur se justifie par là. Encore faut-il qu'il décide sur autre
 * chose qu'un nom. Ces indices ne bloquent rien — refuser les messageries
 * grand public écarterait les très petites entreprises, qui recrutent
 * souvent depuis une adresse personnelle, sans gêner un fraudeur capable
 * d'acheter un domaine. Ils informent, et l'administrateur tranche.
 */
function Qualification({ qualification: q }) {
  if (!q) return null;

  return (
    <div className={`mt-3 rounded-[10px] border p-2.5 ${STYLE_GRAVITE[q.gravite]}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-[11.5px] font-semibold ${COULEUR_GRAVITE[q.gravite]}`}>
          {q.nature}
        </span>
        {q.domaine && (
          <code className="text-[11px] text-txt2 bg-fond/60 px-1.5 py-0.5 rounded">
            {q.domaine}
          </code>
        )}
        {q.comptes_valides_sur_domaine > 0 && (
          <span className="chip bg-succes/15 text-succes text-[10.5px] py-0">
            {q.comptes_valides_sur_domaine} compte(s) déjà validé(s)
          </span>
        )}
      </div>

      {q.indices.length > 0 && (
        <ul className="mt-1.5 space-y-0.5">
          {q.indices.map((i) => (
            <li key={i} className="text-[11.5px] text-txt2 leading-snug">• {i}</li>
          ))}
        </ul>
      )}

      <p className="text-[10.5px] text-txt2 opacity-70 mt-1.5 leading-snug">
        {q.lecture}
      </p>
    </div>
  );
}
