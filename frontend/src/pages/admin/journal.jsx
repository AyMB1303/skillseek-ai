/**
 * Journal d'audit : qui a fait quoi, quand.
 *
 * Le pendant humain de l'explicabilité. Le moteur de score justifie déjà ses
 * décisions ; cet écran fait de même pour celles des personnes — changement de
 * statut, validation de compte, traitement d'un signalement, compte rendu
 * d'entretien.
 *
 * Aucune action n'y est possible : le journal se lit, il ne se modifie pas.
 * Un registre que l'on peut retoucher ne prouve rien.
 */
import { useCallback, useEffect, useState } from "react";
import Layout from "@/components/Layout";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";
import { retard } from "@/lib/mouvement";

const COULEUR_ACTION = {
  candidature_statut: "text-accent",
  evaluation_entretien: "text-cyan",
  signalement_ouvert: "text-alerte",
  signalement_traite: "text-alerte",
  compte_supprime: "text-erreur",
  compte_desactive: "text-erreur",
  compte_refuse: "text-erreur",
  compte_valide: "text-succes",
  compte_restaure: "text-succes",
};

export default function Journal() {
  const { chargement: garde } = useGarde(["admin"]);
  const [entrees, setEntrees] = useState([]);
  const [actions, setActions] = useState([]);
  const [total, setTotal] = useState(0);
  const [filtre, setFiltre] = useState("");
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      const d = await api.journal(filtre);
      setEntrees(d.entrees || []);
      setActions(d.actions || []);
      setTotal(d.total || 0);
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
    }
  }, [filtre]);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  if (garde) return null;

  return (
    <Layout titre="Journal d'audit">
      <div className="space-y-5">
        <header className="space-y-1.5">
          <h1 className="text-xl font-bold">Journal d'audit</h1>
          <p className="text-[13px] text-txt2 leading-relaxed max-w-3xl">
            Toute action significative sur une candidature, un compte ou un
            signalement est consignée ici, avec son auteur et son horodatage.
            Les entrées ne peuvent être ni modifiées ni supprimées.
          </p>
        </header>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={filtre}
            onChange={(e) => setFiltre(e.target.value)}
            aria-label="Filtrer par nature d'action"
            className="champ w-auto py-2 text-[13px]"
          >
            <option value="">Toutes les actions</option>
            {actions.map((a) => (
              <option key={a.code} value={a.code}>{a.libelle}</option>
            ))}
          </select>
          <span className="text-[12px] text-txt2">
            {entrees.length} affichée{entrees.length > 1 ? "s" : ""} sur {total}
          </span>
        </div>

        {etat === "chargement" && <p className="text-sm text-txt2">Chargement…</p>}
        {etat === "erreur" && <p className="text-sm text-erreur">{erreur}</p>}

        {etat === "ok" &&
          (entrees.length === 0 ? (
            <p className="rounded-xl2 border border-bordure bg-surface2/50 p-8 text-center text-sm text-txt2">
              Aucune action consignée pour l'instant. Le journal se remplit dès
              qu'une décision est prise sur une candidature ou un compte.
            </p>
          ) : (
            <ol className="space-y-1.5">
              {entrees.map((e, rang) => (
                <li
                  key={e.id}
                  className="rounded-[10px] border border-bordure bg-surface px-3.5 py-2.5 entree"
                  style={{ animationDelay: retard(rang, 35) }}
                >
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <span
                      className={`text-[13px] font-medium ${
                        COULEUR_ACTION[e.action] || "text-txt"
                      }`}
                    >
                      {e.action_libelle}
                    </span>
                    {e.objet_libelle && (
                      <span className="text-[13px] text-txt2">— {e.objet_libelle}</span>
                    )}
                    <span className="ml-auto text-[11.5px] text-txt2">
                      {new Date(e.created_at).toLocaleString("fr-FR")}
                    </span>
                  </div>

                  <p className="text-[11.5px] text-txt2 mt-0.5">
                    par {e.auteur || "le système"}
                    {Object.keys(e.detail).length > 0 && (
                      <>
                        {" · "}
                        {Object.entries(e.detail)
                          .filter(([, v]) => v !== null && v !== undefined)
                          .map(([k, v]) => `${k.replace(/_/g, " ")} : ${v}`)
                          .join(" · ")}
                      </>
                    )}
                  </p>
                </li>
              ))}
            </ol>
          ))}
      </div>
    </Layout>
  );
}
