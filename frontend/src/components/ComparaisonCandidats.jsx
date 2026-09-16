/** Mise en regard de deux ou trois candidatures d'une même offre.
 *
 * L'écran principal classe ; celui-ci explique un écart. Ce sont deux
 * questions distinctes, et la liste triée ne répond qu'à la première : elle
 * dit qu'un candidat passe devant un autre, jamais pourquoi. Or un écart de
 * quatre points peut venir d'une compétence bloquante absente ou d'un
 * demi-point sur chacune des cinq composantes, et ces deux situations
 * n'appellent pas la même décision.
 *
 * Le parti pris d'affichage suit celui du module de calcul : **rien n'est
 * recalculé, et aucun vainqueur n'est désigné.** Les valeurs viennent toutes
 * de `score_details`. Ce que l'écran ajoute, c'est de mettre en évidence les
 * lignes où les candidatures s'écartent, et de replier celles où elles ne
 * s'écartent pas — une ligne identique chez tout le monde n'apprend rien et
 * éloigne celles qui comptent.
 */
import { useMemo, useState } from "react";
import { Modale } from "./ui";
import { construireComparaison } from "@/lib/comparaison";
import { couleurScore } from "@/lib/scoring";

/* Palette de fond des colonnes : elle sert de repère visuel d'une ligne à
   l'autre, sans hiérarchie. Aucune couleur ne signifie « meilleur ». */
const COLONNES = ["bg-accent/[0.06]", "bg-cyan/[0.06]", "bg-alerte/[0.05]"];

export default function ComparaisonCandidats({ candidatures, onFermer, onOuvrirDetail }) {
  const [replierIdentiques, setReplierIdentiques] = useState(true);
  const comparaison = useMemo(
    () => construireComparaison(candidatures),
    [candidatures]
  );

  const { candidatures: colonnes, offre, composantes, obligatoires, souhaitees } =
    comparaison;

  const visibles = (lignes) =>
    replierIdentiques ? lignes.filter((l) => !l.identique) : lignes;

  const masquees =
    composantes.filter((l) => l.identique).length +
    obligatoires.filter((l) => l.identique).length +
    souhaitees.filter((l) => l.identique).length;

  return (
    <Modale
      ouverte
      onFermer={onFermer}
      largeur="max-w-4xl"
      titre={`Comparer ${colonnes.length} candidatures`}
    >
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-4">
        <span className="text-[13px] text-txt2">
          Offre : <strong className="text-txt">{offre?.title}</strong>
        </span>
        <span className="text-[12.5px] text-txt2">
          {comparaison.nombreDifferences === 0 ? (
            /* Zéro différence est une réponse, pas une absence de réponse :
               elle dit que la note ne tranchera pas et que la décision
               revient entièrement au recruteur. */
            <>Aucune ligne ne les sépare — la note ne les départage pas.</>
          ) : (
            <>
              <strong className="text-txt">{comparaison.nombreDifferences}</strong>{" "}
              ligne{comparaison.nombreDifferences > 1 ? "s" : ""} les sépare
              {comparaison.nombreDifferences > 1 ? "nt" : ""}.
            </>
          )}
        </span>
        {masquees > 0 && (
          <button
            onClick={() => setReplierIdentiques((v) => !v)}
            aria-pressed={!replierIdentiques}
            className="ml-auto text-[12.5px] text-accent hover:text-cyan"
          >
            {replierIdentiques
              ? `Afficher les ${masquees} lignes identiques`
              : "Masquer les lignes identiques"}
          </button>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <caption className="sr-only">
            Comparaison des composantes de la note et des compétences exigées
          </caption>
          <thead>
            <tr>
              <th scope="col" className="text-left px-3 py-2 w-[34%]" />
              {colonnes.map((c, i) => {
                const coul = couleurScore(c.score);
                return (
                  <th
                    key={c.id}
                    scope="col"
                    className={`px-3 py-3 align-bottom text-left ${COLONNES[i]}`}
                  >
                    <div className="font-medium truncate">{c.candidate?.full_name}</div>
                    <div className={`text-lg font-bold ${coul.texte}`}>
                      {c.score}
                      <span className="text-[11px] font-normal text-txt2">/100</span>
                    </div>
                    <button
                      onClick={() => onOuvrirDetail?.(c)}
                      className="text-[11.5px] text-accent hover:text-cyan"
                    >
                      Ouvrir le détail
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>

          <Section titre="Composantes de la note" colonnes={colonnes.length}>
            {visibles(composantes).map((ligne) => (
              <tr key={ligne.libelle} className="border-t border-bordure">
                <th scope="row" className="text-left font-normal px-3 py-2 text-txt2">
                  {ligne.libelle}
                  <span className="text-[11px] text-txt2/70"> · sur {ligne.max}</span>
                </th>
                {ligne.valeurs.map((valeur, i) => (
                  <td key={i} className={`px-3 py-2 ${COLONNES[i]}`}>
                    {valeur == null ? (
                      /* « Non applicable » et « zéro point » sont deux
                         informations différentes : le moteur omet une
                         composante qu'il n'a pas pu calculer, et l'afficher
                         à zéro ferait passer le candidat pour mauvais là où
                         la question ne lui a pas été posée. */
                      <span className="text-txt2/60 text-[12px]">non calculée</span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <span
                          className={
                            !ligne.identique && valeur === ligne.meilleure
                              ? "font-semibold text-txt"
                              : "text-txt2"
                          }
                        >
                          {valeur}
                        </span>
                        <span className="h-1.5 flex-1 max-w-[70px] rounded bg-bordure/60 overflow-hidden">
                          <span
                            className="block h-full bg-accent/70"
                            style={{ width: `${Math.round((valeur / ligne.max) * 100)}%` }}
                          />
                        </span>
                      </span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </Section>

          <Section titre="Compétences obligatoires" colonnes={colonnes.length}>
            {visibles(obligatoires).map((ligne) => (
              <LigneCompetence key={ligne.competence} ligne={ligne} />
            ))}
          </Section>

          {souhaitees.length > 0 && (
            <Section titre="Compétences souhaitées" colonnes={colonnes.length}>
              {visibles(souhaitees).map((ligne) => (
                <LigneCompetence key={ligne.competence} ligne={ligne} />
              ))}
            </Section>
          )}

          {comparaison.eliminatoires.some((e) => e.eliminatoires.length) && (
            <Section titre="Critères éliminatoires" colonnes={colonnes.length}>
              <tr className="border-t border-bordure">
                <th scope="row" className="text-left font-normal px-3 py-2 text-txt2 align-top">
                  Motifs d'écartement
                </th>
                {comparaison.eliminatoires.map((e, i) => (
                  <td key={e.id} className={`px-3 py-2 align-top ${COLONNES[i]}`}>
                    {e.eliminatoires.length === 0 ? (
                      <span className="text-succes text-[12px]">Aucun</span>
                    ) : (
                      <ul className="space-y-1">
                        {e.eliminatoires.map((motif) => (
                          <li key={motif} className="text-alerte text-[12px]">
                            {motif}
                          </li>
                        ))}
                      </ul>
                    )}
                  </td>
                ))}
              </tr>
            </Section>
          )}
        </table>
      </div>

      {/* Un critère éliminatoire plafonne la note au lieu d'en retirer des
          points : l'écart qu'il produit n'est pas de degré mais de nature, et
          le lire comme les autres conduirait à une mauvaise décision. */}
      {comparaison.eliminatoires.some((e) => e.eliminatoires.length) && (
        <p className="mt-4 text-[12px] text-txt2 bg-surface border border-bordure rounded-[10px] px-3.5 py-2.5">
          Un critère éliminatoire ne retire pas des points : il plafonne la note.
          L'écart qu'il produit se lit donc comme une différence de nature, non de degré.
        </p>
      )}

      <p className="mt-3 text-[12px] text-txt2">
        Cette vue n'ordonne rien et ne recalcule rien : elle reprend les valeurs
        déjà justifiées par le moteur. La décision reste la vôtre.
      </p>
    </Modale>
  );
}

/** Bandeau de section à l'intérieur du tableau. */
function Section({ titre, colonnes, children }) {
  const lignes = Array.isArray(children) ? children.filter(Boolean) : children;
  if (Array.isArray(lignes) && lignes.length === 0) return null;
  return (
    <tbody>
      <tr>
        <th
          scope="colgroup"
          colSpan={colonnes + 1}
          className="text-left text-[11px] uppercase tracking-wide text-txt2 pt-5 pb-1 px-3"
        >
          {titre}
        </th>
      </tr>
      {lignes}
    </tbody>
  );
}

function LigneCompetence({ ligne }) {
  return (
    <tr className="border-t border-bordure">
      <th scope="row" className="text-left font-normal px-3 py-2 text-txt2">
        {ligne.competence}
        {ligne.absenteChezTous && (
          /* Une compétence que personne ne détient dit quelque chose de
             l'offre, pas des candidats. La signaler évite qu'elle ne soit
             lue comme un reproche adressé à chacun. */
          <span className="text-[11px] text-txt2/70"> · exigée, absente partout</span>
        )}
      </th>
      {ligne.detentions.map((detenue, i) => (
        <td key={i} className={`px-3 py-2 ${COLONNES[i]}`}>
          {detenue ? (
            <span className="text-succes text-[13px]">
              <span aria-hidden="true">✓</span>
              <span className="sr-only">détenue</span>
            </span>
          ) : (
            <span className="text-txt2/70 text-[13px]">
              <span aria-hidden="true">—</span>
              <span className="sr-only">absente</span>
            </span>
          )}
        </td>
      ))}
    </tr>
  );
}
