/** Corbeille : éléments supprimés, restaurables ou effaçables définitivement. */
import { useEffect, useState, useCallback } from "react";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur, EtatVide, Modale, useToast } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";

const ONGLETS = [
  { cle: "users", libelle: "Comptes" },
  { cle: "offers", libelle: "Offres" },
];

export default function AdminCorbeille() {
  const { chargement: garde } = useGarde(["admin"]);
  const { notifier } = useToast();

  const [contenu, setContenu] = useState({ users: [], offers: [] });
  const [onglet, setOnglet] = useState("users");
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");
  const [aPurger, setAPurger] = useState(null);

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      const d = await api.corbeille();
      setContenu({ users: d.users, offers: d.offers });
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
    }
  }, []);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  const restaurer = async (element) => {
    const compte = onglet === "users";
    try {
      await (compte ? api.restaurerUtilisateur(element.id) : api.restaurerOffre(element.id));
      setContenu((c) => ({ ...c, [onglet]: c[onglet].filter((x) => x.id !== element.id) }));
      notifier(`${compte ? element.full_name : element.title} restauré.`);
    } catch (e) {
      notifier(e.message, { type: "erreur" });
    }
  };

  const purger = async () => {
    const compte = aPurger.type === "users";
    try {
      await (compte ? api.purgerUtilisateur(aPurger.id) : api.purgerOffre(aPurger.id));
      setContenu((c) => ({
        ...c,
        [aPurger.type]: c[aPurger.type].filter((x) => x.id !== aPurger.id),
      }));
      notifier("Suppression définitive effectuée.");
    } catch (e) {
      notifier(e.message, { type: "erreur" });
    } finally {
      setAPurger(null);
    }
  };

  if (garde) return null;

  const elements = contenu[onglet];

  return (
    <Layout titre="Corbeille">
      <p className="text-sm text-txt2 mb-5 max-w-2xl">
        Les éléments supprimés sont conservés ici plutôt qu'effacés immédiatement. Ils peuvent
        être restaurés à tout moment ; la suppression définitive reste possible, sauf lorsque
        des candidatures y sont rattachées.
      </p>

      <div className="flex gap-1 border-b border-bordure mb-5">
        {ONGLETS.map((o) => (
          <button
            key={o.cle}
            onClick={() => setOnglet(o.cle)}
            role="tab"
            aria-selected={onglet === o.cle}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              onglet === o.cle ? "border-accent text-txt" : "border-transparent text-txt2 hover:text-txt"
            }`}
          >
            {o.libelle}
            <span className="ml-2 text-xs text-txt2">{contenu[o.cle].length}</span>
          </button>
        ))}
      </div>

      {etat === "chargement" && <Chargement lignes={3} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" &&
        (elements.length === 0 ? (
          <EtatVide
            titre="Corbeille vide"
            description={`Aucun ${onglet === "users" ? "compte" : "offre"} supprimé.`}
          />
        ) : (
          <div className="carte divide-y divide-bordure">
            {elements.map((el) => (
              <div key={el.id} className="flex flex-wrap items-center gap-4 px-5 py-3.5">
                <div className="flex-1 min-w-[200px]">
                  <p className="font-medium text-sm">
                    {onglet === "users" ? el.full_name : el.title}
                  </p>
                  <p className="text-xs text-txt2 mt-0.5">
                    {onglet === "users" ? el.email : el.company || "offre"}
                    {el.deleted_at && (
                      <> · supprimé le {new Date(el.deleted_at).toLocaleDateString("fr-FR")}</>
                    )}
                  </p>
                </div>

                <div className="flex gap-2">
                  <button onClick={() => restaurer(el)} className="btn-secondaire text-succes">
                    Restaurer
                  </button>
                  <button
                    onClick={() => setAPurger({ ...el, type: onglet })}
                    className="btn-fantome text-erreur hover:bg-erreur/10"
                  >
                    Supprimer définitivement
                  </button>
                </div>
              </div>
            ))}
          </div>
        ))}

      <Modale
        ouverte={!!aPurger}
        onFermer={() => setAPurger(null)}
        titre="Suppression définitive"
        actions={
          <>
            <button onClick={() => setAPurger(null)} className="btn-fantome">Annuler</button>
            <button onClick={purger} className="btn bg-erreur text-white hover:opacity-90">
              Supprimer définitivement
            </button>
          </>
        }
      >
        <p className="text-sm">
          <strong>{aPurger?.full_name || aPurger?.title}</strong> sera effacé de façon
          irréversible.
        </p>
        <p className="text-xs text-txt2 mt-2">
          Cette action ne peut pas être annulée. Préférez la restauration en cas de doute.
        </p>
      </Modale>
    </Layout>
  );
}
