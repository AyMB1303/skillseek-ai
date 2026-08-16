/**
 * Saisie de compétences par étiquettes, adossée au référentiel du moteur.
 *
 * Le composant règle un problème de fond, pas seulement d'ergonomie. Le moteur
 * d'analyse ne sait rapprocher un curriculum d'une offre que si la compétence
 * exigée appartient à son référentiel. Un recruteur qui écrit « postgres » au
 * lieu de « postgresql » rend l'exigence introuvable, et tous les candidats
 * sont écartés pour une compétence qu'ils possèdent — sans le moindre message
 * d'erreur. La saisie libre est donc un piège silencieux.
 *
 * Trois garde-fous y répondent : les suggestions viennent du référentiel, les
 * synonymes connus sont convertis automatiquement (« JS » devient
 * « javascript »), et toute saisie non reconnue est acceptée mais signalée.
 * Acceptée, car le référentiel est incomplet par nature et le recruteur reste
 * maître de son offre ; signalée, pour qu'il sache ce qu'il fait.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";

// Le referentiel ne change pas d'une session a l'autre : le charger une fois
// pour toute l'application evite une requete par formulaire ouvert.
let cacheReferentiel = null;

export default function SaisieCompetences({
  valeurs,
  onChange,
  id,
  placeholder = "Saisissez une compétence puis Entrée",
  couleur = "accent",
}) {
  const [saisie, setSaisie] = useState("");
  const [referentiel, setReferentiel] = useState(cacheReferentiel);
  const [indexActif, setIndexActif] = useState(0);
  const [focus, setFocus] = useState(false);
  const champRef = useRef(null);

  useEffect(() => {
    if (cacheReferentiel) return;
    api
      .referentielCompetences()
      .then((d) => {
        cacheReferentiel = d;
        setReferentiel(d);
      })
      .catch(() => {
        /* sans référentiel, la saisie reste libre : ne jamais bloquer */
      });
  }, []);

  // Memorisees : sans cela, `|| []` cree un tableau neuf a chaque rendu et
  // le calcul des suggestions se relance meme quand rien n'a change.
  const connues = useMemo(() => referentiel?.competences || [], [referentiel]);
  const variantes = useMemo(() => referentiel?.variantes || {}, [referentiel]);

  /** Ramène une saisie à sa forme canonique lorsqu'elle est connue. */
  const canoniser = (brute) => {
    const v = brute.trim().toLowerCase();
    return variantes[v] || v;
  };

  const suggestions = useMemo(() => {
    const q = saisie.trim().toLowerCase();
    if (!q) return [];
    const deja = new Set(valeurs);
    return connues
      .filter((c) => c.includes(q) && !deja.has(c))
      .slice(0, 6);
  }, [saisie, connues, valeurs]);

  const ajouter = (brute) => {
    const v = canoniser(brute);
    if (!v) return;
    if (!valeurs.includes(v)) onChange([...valeurs, v]);
    setSaisie("");
    setIndexActif(0);
  };

  const retirer = (c) => onChange(valeurs.filter((x) => x !== c));

  const auClavier = (e) => {
    if (e.key === "ArrowDown" && suggestions.length) {
      e.preventDefault();
      setIndexActif((i) => (i + 1) % suggestions.length);
      return;
    }
    if (e.key === "ArrowUp" && suggestions.length) {
      e.preventDefault();
      setIndexActif((i) => (i - 1 + suggestions.length) % suggestions.length);
      return;
    }
    // Entrée et virgule valident : la virgule est le réflexe naturel quand on
    // énumère, autant l'accepter plutôt que de produire « sql, java » en un bloc.
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      ajouter(suggestions[indexActif] || saisie);
      return;
    }
    // Retour arrière sur un champ vide : retire la dernière étiquette.
    if (e.key === "Backspace" && !saisie && valeurs.length) {
      onChange(valeurs.slice(0, -1));
    }
  };

  // Compétences saisies que le moteur ne saura pas reconnaître.
  const inconnues = referentiel
    ? valeurs.filter((v) => !connues.includes(v))
    : [];

  const styleChip =
    couleur === "cyan"
      ? "bg-cyan/15 text-cyan hover:bg-erreur/15 hover:text-erreur"
      : "bg-accent/15 text-accent hover:bg-erreur/15 hover:text-erreur";

  return (
    <div className="relative">
      {/* Le cadre entier se comporte comme un champ : les étiquettes occupent
          la ligne et la zone de frappe se décale à leur suite. */}
      <div
        onClick={() => champRef.current?.focus()}
        className={`champ flex flex-wrap items-center gap-1.5 min-h-[44px] cursor-text py-2 ${
          focus ? "border-accent" : ""
        }`}
      >
        {valeurs.map((c) => (
          <span
            key={c}
            className={`chip text-[12px] py-0.5 gap-1 ${styleChip} ${
              inconnues.includes(c) ? "ring-1 ring-alerte/60" : ""
            }`}
          >
            {c}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                retirer(c);
              }}
              aria-label={`Retirer ${c}`}
              className="opacity-70 hover:opacity-100"
            >
              ×
            </button>
          </span>
        ))}

        <input
          ref={champRef}
          id={id}
          value={saisie}
          onChange={(e) => setSaisie(e.target.value)}
          onKeyDown={auClavier}
          onFocus={() => setFocus(true)}
          onBlur={() => {
            setFocus(false);
            // Ne pas perdre une saisie en cours parce qu'on a cliqué ailleurs.
            if (saisie.trim()) ajouter(saisie);
          }}
          placeholder={valeurs.length === 0 ? placeholder : ""}
          className="flex-1 min-w-[9rem] bg-transparent border-0 outline-none text-sm py-0.5"
          autoComplete="off"
          role="combobox"
          aria-expanded={suggestions.length > 0}
          aria-autocomplete="list"
          aria-controls="liste-suggestions-competences"
        />
      </div>

      {/* Suggestions issues du référentiel */}
      {focus && suggestions.length > 0 && (
        <ul
          id="liste-suggestions-competences"
          className="absolute z-20 left-0 right-0 mt-1 rounded-[10px] border border-bordure
                     bg-surface shadow-lg overflow-hidden"
          role="listbox"
        >
          {suggestions.map((s, i) => (
            <li key={s}>
              <button
                type="button"
                // `onMouseDown` plutôt que `onClick` : le clic arriverait après
                // le `blur`, qui aurait déjà validé la saisie brute.
                onMouseDown={(e) => {
                  e.preventDefault();
                  ajouter(s);
                }}
                onMouseEnter={() => setIndexActif(i)}
                className={`w-full text-left px-3 py-2 text-[13px] transition-colors ${
                  i === indexActif ? "bg-accent/12 text-accent" : "hover:bg-surface2"
                }`}
                role="option"
                aria-selected={i === indexActif}
              >
                {s}
              </button>
            </li>
          ))}
        </ul>
      )}

      {inconnues.length > 0 && (
        <p className="text-[11px] text-alerte mt-1.5 leading-snug">
          {inconnues.join(", ")} {inconnues.length > 1 ? "ne figurent" : "ne figure"} pas
          au référentiel du moteur : la compétence sera exigée mais jamais détectée
          dans les CV, et toutes les candidatures seront écartées. Vérifiez
          l'orthographe ou retirez-la.
        </p>
      )}
    </div>
  );
}
