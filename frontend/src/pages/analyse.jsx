/**
 * Analyse décisionnelle du portefeuille de candidatures.
 *
 * Le tableau de bord répond à « combien ». Cette page répond à « pourquoi » —
 * et surtout à la question qu'aucun système de présélection ne se pose
 * habituellement : **est-ce que mon classement vaut quelque chose ?**
 *
 * La confrontation entre la note calculée avant l'entretien et le verdict
 * porté après est le seul juge honnête du moteur. Pas un corpus public et
 * anglophone : les candidats réellement reçus, par ces recruteurs-là. Elle
 * est affichée telle quelle, y compris quand elle est défavorable au système.
 *
 * Trois sections, dans l'ordre de ce qu'un recruteur veut savoir : comment
 * ses candidats se répartissent, ce qui les écarte, et ce que le système
 * vaut face à son propre jugement.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Layout from "@/components/Layout";
import { Chargement, EtatErreur } from "@/components/ui";
import { useGarde } from "@/lib/auth";
import { api } from "@/lib/api";
import { useCompteur, useEntreeEnVue, retard } from "@/lib/mouvement";

const PERIODES = [
  { valeur: 30, libelle: "30 jours" },
  { valeur: 90, libelle: "90 jours" },
  { valeur: 365, libelle: "1 an" },
];

export default function Analyse() {
  // Recruteur seulement. La page montre des noms de candidats et s'appuie sur
  // `view_dashboard` : l'administrateur ne détient ni l'un ni l'autre, et lui
  // ouvrir cet écran contournerait la même règle que pour l'assistant.
  const { chargement: garde } = useGarde(["recruiter"]);
  const [periode, setPeriode] = useState(90);
  const [donnees, setDonnees] = useState(null);
  const [comparaison, setComparaison] = useState(null);
  const [controles, setControles] = useState(null);
  const [etat, setEtat] = useState("chargement");
  const [erreur, setErreur] = useState("");

  const charger = useCallback(async () => {
    setEtat("chargement");
    try {
      setDonnees(await api.analyse(periode));
      setEtat("ok");
    } catch (e) {
      setErreur(e.message);
      setEtat("erreur");
      return;
    }
    // Les deux suivantes sont facultatives : la page reste utile sans elles.
    api.comparaisonEvaluations().then(setComparaison).catch(() => {});
    api.syntheseControles().then(setControles).catch(() => {});
  }, [periode]);

  useEffect(() => {
    if (!garde) charger();
  }, [garde, charger]);

  if (garde) return null;

  return (
    <Layout titre="Analyse">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <p className="text-[13px] text-txt2 max-w-2xl leading-relaxed">
          Comment les candidatures se répartissent, ce qui les écarte, et ce
          que vaut le classement du système face à votre propre jugement.
        </p>
        <div className="flex gap-1 bg-surface2 rounded-[10px] p-1 shrink-0">
          {PERIODES.map((p) => (
            <button
              key={p.valeur}
              onClick={() => setPeriode(p.valeur)}
              className={`px-3 py-1.5 rounded-[7px] text-[12.5px] font-medium transition-colors ${
                periode === p.valeur ? "bg-accent text-white" : "text-txt2 hover:text-txt"
              }`}
              aria-pressed={periode === p.valeur}
            >
              {p.libelle}
            </button>
          ))}
        </div>
      </div>

      {etat === "chargement" && <Chargement lignes={4} />}
      {etat === "erreur" && <EtatErreur message={erreur} onReessayer={charger} />}

      {etat === "ok" && donnees && (
        <div className="space-y-6">
          <Reperes donnees={donnees} />
          <Distribution donnees={donnees} />

          <div className="grid gap-5 xl:grid-cols-2 items-start">
            <Palmares
              titre="Ce qui écarte le plus souvent"
              aide="Motifs éliminatoires, regroupés par nature. Un motif fréquent
                    signale souvent une exigence mal calibrée plutôt qu'un marché pauvre."
              elements={donnees.motifs_ecartement}
              couleur="bg-erreur"
              vide="Aucune candidature n'a été écartée par une règle sur la période."
            />
            <Palmares
              titre="Compétences les plus souvent absentes"
              aide="Sur l'ensemble des dossiers reçus. C'est la lecture la plus
                    directe de l'écart entre ce que vous demandez et ce que le
                    marché local propose."
              elements={donnees.competences_manquantes}
              couleur="bg-alerte"
              vide="Toutes les compétences obligatoires étaient présentes."
            />
          </div>

          {donnees.reserves?.length > 0 && (
            <Palmares
              titre="Réserves les plus fréquentes"
              aide="Écarts mesurés qui n'éliminent pas : le candidat reste dans le
                    classement, et vous décidez vous-même de leur portée."
              elements={donnees.reserves}
              couleur="bg-cyan"
            />
          )}

          <Comparaison donnees={comparaison} />
          <Controles donnees={controles} />
        </div>
      )}
    </Layout>
  );
}

/* ------------------------------------------------------------------ */

function Reperes({ donnees }) {
  const cartes = [
    { libelle: "Candidatures sur la période", valeur: donnees.effectif },
    { libelle: "Note médiane", valeur: donnees.note_mediane, suffixe: "/100", accent: "accent" },
    {
      libelle: "Délai avant première décision",
      valeur: donnees.delai_median_jours,
      suffixe: " j",
      accent: "cyan",
      aide: "Médiane, lue dans le journal d'audit",
    },
    {
      libelle: "En attente de décision",
      valeur: donnees.en_attente,
      accent: donnees.en_attente > 0 ? "alerte" : undefined,
      aide: donnees.attente_la_plus_ancienne_jours
        ? `La plus ancienne date de ${donnees.attente_la_plus_ancienne_jours} jours`
        : undefined,
    },
  ];

  return (
    <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cartes.map((c, i) => (
        <Repere key={c.libelle} {...c} rang={i} />
      ))}
    </section>
  );
}

function Repere({ libelle, valeur, suffixe, accent, aide, rang }) {
  const couleurs = { accent: "text-accent", cyan: "text-cyan", alerte: "text-alerte" };
  const affiche = useCompteur(valeur ?? 0, { duree: 800 });
  return (
    <div className="carte carte-reactive p-4 entree" style={{ animationDelay: retard(rang, 60) }}>
      <p className={`text-2xl font-bold tabular-nums ${couleurs[accent] || "text-txt"}`}
         aria-label={`${libelle} : ${valeur ?? "non disponible"}`}>
        {valeur == null ? "—" : <>{affiche}<span className="text-base font-medium">{suffixe}</span></>}
      </p>
      <p className="text-[11.5px] text-txt2 mt-0.5 leading-snug">{libelle}</p>
      {aide && <p className="text-[10.5px] text-txt2 opacity-70 mt-1 leading-snug">{aide}</p>}
    </div>
  );
}

/** Répartition des notes, barres verticales. */
function Distribution({ donnees }) {
  const [ancre, visible] = useEntreeEnVue();
  const max = Math.max(...donnees.distribution.map((d) => d.effectif), 1);

  return (
    <section className="carte p-5" ref={ancre}>
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
        <h2 className="font-semibold text-sm">Répartition des notes</h2>
        <span className="text-[11.5px] text-txt2">
          {donnees.analysees} candidature(s) analysée(s)
        </span>
      </div>
      <p className="text-[11.5px] text-txt2 mb-5 max-w-2xl leading-snug">
        Les tranches suivent la lecture métier : 50 sépare les candidatures
        retenues des écartées, 70 marque le profil très adapté. Une masse
        concentrée sous 50 indique une offre trop exigeante bien plus souvent
        qu'un vivier insuffisant.
      </p>

      <div className="flex items-end gap-2 h-44">
        {donnees.distribution.map((d, i) => {
          const hauteur = (d.effectif / max) * 100;
          return (
            <div key={d.tranche} className="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
              <span className="text-[11.5px] font-semibold tabular-nums">{d.effectif}</span>
              <div
                className={`w-full rounded-t-[5px] ${d.retenu ? "bg-accent" : "bg-bordure"} ${
                  visible ? "barre-montante" : ""
                }`}
                style={{
                  height: `${Math.max(hauteur, d.effectif ? 3 : 0)}%`,
                  animationDelay: retard(i, 80),
                }}
                title={`${d.effectif} candidature(s) entre ${d.tranche}`}
              />
              <span className="text-[10.5px] text-txt2 whitespace-nowrap">{d.tranche}</span>
            </div>
          );
        })}
      </div>

      <p className="text-[11px] text-txt2 mt-4 pt-3 border-t border-bordure">
        {/* Les espaces sont explicites : entre un élément et le texte qui le
            suit, un simple retour à la ligne en JSX produit une espace, mais
            rien ne dit au lecteur si elle est voulue. */}
        <span className="inline-block w-2.5 h-2.5 rounded-sm bg-accent align-middle mr-1.5" />
        {" "}
        Au-dessus du seuil de présélection
        {" "}
        <span className="inline-block w-2.5 h-2.5 rounded-sm bg-bordure align-middle ml-4 mr-1.5" />
        {" "}
        Écartées du classement, consultables et repêchables
      </p>
    </section>
  );
}

/** Classement horizontal : motifs, compétences, réserves. */
function Palmares({ titre, aide, elements, couleur, vide }) {
  const [ancre, visible] = useEntreeEnVue();
  const max = Math.max(...(elements || []).map((e) => e.effectif), 1);

  return (
    <section className="carte p-5" ref={ancre}>
      <h2 className="font-semibold text-sm">{titre}</h2>
      {aide && <p className="text-[11.5px] text-txt2 mt-1 mb-4 leading-snug">{aide}</p>}

      {!elements?.length ? (
        <p className="text-[12.5px] text-txt2 py-4">{vide || "Aucune donnée sur la période."}</p>
      ) : (
        <div className="space-y-2.5">
          {elements.map((e, i) => (
            <div key={e.libelle}>
              <div className="flex justify-between gap-3 text-xs mb-1">
                <span className="truncate" title={e.libelle}>{e.libelle}</span>
                <span className="text-txt2 tabular-nums shrink-0">{e.effectif}</span>
              </div>
              <div className="h-1.5 bg-fond rounded-full overflow-hidden">
                <div
                  className={`h-full ${couleur} rounded-full ${visible ? "jauge-remplissage" : ""}`}
                  style={{
                    width: `${(e.effectif / max) * 100}%`,
                    animationDelay: retard(i, 60),
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

/**
 * Confrontation de la note calculée au verdict d'entretien.
 *
 * Les deux erreurs n'ont pas le même coût, et c'est pour cela qu'elles sont
 * comptées séparément. Un « faux espoir » fait perdre une heure d'entretien ;
 * une « pépite manquée » fait perdre un candidat, définitivement.
 */
function Comparaison({ donnees }) {
  if (!donnees) return null;

  if (!donnees.effectif) {
    return (
      <section className="carte p-5">
        <h2 className="font-semibold text-sm">Le classement tient-il ses promesses ?</h2>
        <p className="text-[12.5px] text-txt2 mt-2 max-w-2xl leading-relaxed">
          {donnees.message}
        </p>
        <p className="text-[11.5px] text-txt2 mt-3">
          Renseignez la grille d'entretien depuis le détail d'une candidature :
          c'est ce qui permet de confronter la note calculée avant à
          l'appréciation portée après.
        </p>
      </section>
    );
  }

  const cartes = [
    { libelle: "Comptes rendus", valeur: donnees.effectif },
    {
      libelle: "Écart moyen avec la note",
      valeur: donnees.ecart_absolu_moyen,
      suffixe: " pts",
      accent: "accent",
    },
    { libelle: "Jugements concordants", valeur: donnees.part_concordante, suffixe: " %", accent: "cyan" },
    {
      libelle: "Pépites manquées",
      valeur: donnees.pepites_manquees,
      accent: donnees.pepites_manquees > 0 ? "alerte" : undefined,
      aide: "Écartés par le système, retenus en entretien",
    },
  ];

  return (
    <section className="space-y-3">
      <div>
        <h2 className="font-semibold text-sm">Le classement tient-il ses promesses ?</h2>
        <p className="text-[11.5px] text-txt2 mt-1 max-w-3xl leading-relaxed">
          La note est calculée avant l'entretien, le verdict porté après. Les
          confronter est le seul moyen honnête de savoir ce que vaut le
          classement — non pas sur un corpus public, mais sur les candidats que
          vous avez réellement reçus. Un écart positif signifie que le système
          note plus généreusement que vous.
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {cartes.map((c, i) => <Repere key={c.libelle} {...c} rang={i} />)}
      </div>

      {donnees.faux_espoirs > 0 && (
        <p className="text-[12px] text-txt2">
          {donnees.faux_espoirs} candidature(s) retenue(s) par le système puis
          écartée(s) en entretien. Une heure perdue ; une pépite manquée coûte
          bien plus cher.
        </p>
      )}

      {donnees.detail?.length > 0 && (
        <div className="carte overflow-hidden">
          <div className="px-5 py-3 border-b border-bordure">
            <h3 className="text-[12.5px] font-semibold">Les écarts les plus marqués</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-txt2 border-b border-bordure">
                  <th className="px-5 py-2.5 font-medium">Candidat</th>
                  <th className="px-5 py-2.5 font-medium">Offre</th>
                  <th className="px-5 py-2.5 font-medium">Système</th>
                  <th className="px-5 py-2.5 font-medium">Entretien</th>
                  <th className="px-5 py-2.5 font-medium">Écart</th>
                  <th className="px-5 py-2.5 font-medium">Verdict</th>
                </tr>
              </thead>
              <tbody>
                {donnees.detail.slice(0, 8).map((d, i) => (
                  <tr
                    key={`${d.candidat}-${i}`}
                    className="border-b border-bordure last:border-0 entree"
                    style={{ animationDelay: retard(i, 40) }}
                  >
                    <td className="px-5 py-2.5">{d.candidat || "—"}</td>
                    <td className="px-5 py-2.5 text-txt2">{d.offre || "—"}</td>
                    <td className="px-5 py-2.5 tabular-nums">{d.score_systeme}</td>
                    <td className="px-5 py-2.5 tabular-nums">{d.note_humaine}</td>
                    <td className={`px-5 py-2.5 tabular-nums font-medium ${
                      d.ecart > 0 ? "text-alerte" : "text-cyan"
                    }`}>
                      {d.ecart > 0 ? "+" : ""}{d.ecart}
                    </td>
                    <td className="px-5 py-2.5 text-txt2">{d.verdict}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

/** Synthèse des contrôles d'anomalies. */
function Controles({ donnees }) {
  if (!donnees || !donnees.total) return null;

  return (
    <section className="carte p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-semibold text-sm">Contrôle des dossiers</h2>
        <Link href="/signalements" className="text-[12.5px] text-accent hover:text-cyan">
          Ouvrir le contrôle →
        </Link>
      </div>
      <p className="text-[11.5px] text-txt2 mt-1 mb-4 leading-snug">
        Aucun signalement ne modifie une note. Ils ouvrent une vérification
        humaine, dont la décision est conservée.
      </p>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Repere libelle="Signalements" valeur={donnees.total} rang={0} />
        <Repere libelle="Dossiers concernés" valeur={donnees.candidatures_concernees} rang={1} />
        <Repere
          libelle="À trancher"
          valeur={donnees.a_traiter}
          accent={donnees.a_traiter > 0 ? "alerte" : undefined}
          rang={2}
        />
        <Repere
          libelle="Confirmés après examen"
          valeur={donnees.confirmes}
          aide={`${donnees.ecartes} écarté(s) par un recruteur`}
          rang={3}
        />
      </div>
    </section>
  );
}
