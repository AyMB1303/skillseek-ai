/**
 * Visite guidée : présentation de l'interface à la première connexion.
 *
 * Un utilisateur qui découvre la plateforme ne sait pas ce qu'elle sait faire,
 * et rien dans une interface bien rangée ne le lui dit. La visite comble ce
 * vide en désignant les éléments réels de l'écran plutôt qu'en décrivant des
 * captures : ce qui est montré est ce qui sera cliqué.
 *
 * Trois principes de conception :
 *
 *   1. **Interruptible à tout moment.** Un tutoriel qu'on ne peut pas fermer
 *      est une porte close. « Passer » est visible dès la première étape, et
 *      la touche Échap fonctionne partout.
 *   2. **Rejouable.** La visite est accessible depuis le menu du profil, donc
 *      elle n'est pas perdue si elle a été passée trop vite.
 *   3. **Ancrée sur des éléments permanents.** Les étapes visent la barre
 *      latérale et l'en-tête, présents sur toutes les pages : la visite ne
 *      dépend donc pas de l'écran sur lequel l'utilisateur a atterri.
 *
 * L'animation est désactivée si le système signale une préférence pour un
 * mouvement réduit : un effet décoratif ne doit pas gêner qui le supporte mal.
 */
import { useCallback, useEffect, useLayoutEffect, useState } from "react";

const MARGE = 8;          // respiration autour de l'élément mis en avant
const LARGEUR_BULLE = 340;

export default function VisiteGuidee({ etapes, onFermer }) {
  const [index, setIndex] = useState(0);
  const [zone, setZone] = useState(null);
  const [sobre, setSobre] = useState(false);

  const etape = etapes[index];
  const derniere = index === etapes.length - 1;

  useEffect(() => {
    const requete = window.matchMedia("(prefers-reduced-motion: reduce)");
    setSobre(requete.matches);
  }, []);

  // Position de l'élément visé, recalculée à chaque étape et à chaque
  // changement de géométrie : une barre latérale repliée déplace tout.
  const mesurer = useCallback(() => {
    if (!etape?.cible) return setZone(null);
    const noeud = document.querySelector(etape.cible);
    if (!noeud) return setZone(null);
    const r = noeud.getBoundingClientRect();
    if (!r.width && !r.height) return setZone(null);
    setZone({
      haut: r.top - MARGE,
      gauche: r.left - MARGE,
      largeur: r.width + MARGE * 2,
      hauteur: r.height + MARGE * 2,
    });
  }, [etape]);

  useLayoutEffect(() => {
    const noeud = etape?.cible && document.querySelector(etape.cible);
    noeud?.scrollIntoView({ block: "center", behavior: sobre ? "auto" : "smooth" });
    // Un court délai laisse le défilement s'achever avant la mesure.
    const t = setTimeout(mesurer, sobre ? 0 : 180);
    return () => clearTimeout(t);
  }, [mesurer, etape, sobre]);

  useEffect(() => {
    window.addEventListener("resize", mesurer);
    window.addEventListener("scroll", mesurer, true);
    return () => {
      window.removeEventListener("resize", mesurer);
      window.removeEventListener("scroll", mesurer, true);
    };
  }, [mesurer]);

  const suivant = useCallback(
    () => (derniere ? onFermer(true) : setIndex((i) => i + 1)),
    [derniere, onFermer]
  );

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onFermer(false);
      if (e.key === "ArrowRight" || e.key === "Enter") { e.preventDefault(); suivant(); }
      if (e.key === "ArrowLeft") setIndex((i) => Math.max(0, i - 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [suivant, onFermer]);

  if (!etape) return null;

  const bulle = positionner(zone);

  return (
    <div
      className="fixed inset-0 z-[100]"
      role="dialog"
      aria-modal="true"
      aria-label={`Visite guidée, étape ${index + 1} sur ${etapes.length}`}
    >
      <style>{CSS_VISITE}</style>

      {/* Voile en quatre volets : la découpe laisse l'élément visé net et
          lisible, là où un voile plein l'aurait masqué avec le reste. */}
      {zone ? (
        <>
          <Voile style={{ top: 0, left: 0, right: 0, height: Math.max(0, zone.haut) }} />
          <Voile style={{ top: zone.haut + zone.hauteur, left: 0, right: 0, bottom: 0 }} />
          <Voile style={{ top: zone.haut, left: 0, width: Math.max(0, zone.gauche), height: zone.hauteur }} />
          <Voile style={{ top: zone.haut, left: zone.gauche + zone.largeur, right: 0, height: zone.hauteur }} />
          <div
            className={`absolute rounded-[12px] pointer-events-none ${sobre ? "" : "visite-halo"}`}
            style={{
              top: zone.haut, left: zone.gauche,
              width: zone.largeur, height: zone.hauteur,
              border: "2px solid var(--accent, #3B82F6)",
            }}
          />
        </>
      ) : (
        <Voile style={{ inset: 0 }} onClick={() => onFermer(false)} />
      )}

      {/* Bulle explicative */}
      <div
        className={`absolute carte bg-surface2 shadow-2xl p-4 space-y-3 ${sobre ? "" : "visite-entree"}`}
        style={{ ...bulle, width: LARGEUR_BULLE, maxWidth: "calc(100vw - 24px)" }}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-wide text-accent font-semibold">
              Étape {index + 1} sur {etapes.length}
            </p>
            <h2 className="font-bold text-[15px] mt-0.5">{etape.titre}</h2>
          </div>
          <button
            onClick={() => onFermer(false)}
            className="text-txt2 hover:text-txt text-lg leading-none shrink-0"
            aria-label="Fermer la visite"
          >
            ×
          </button>
        </div>

        <p className="text-[13px] text-txt2 leading-relaxed">{etape.texte}</p>

        <div className="flex items-center justify-between gap-3 pt-1">
          <div className="flex gap-1.5" aria-hidden="true">
            {etapes.map((_, i) => (
              <span
                key={i}
                className={`h-1.5 rounded-full transition-all duration-200 ${
                  i === index ? "w-5 bg-accent" : "w-1.5 bg-bordure"
                }`}
              />
            ))}
          </div>

          <div className="flex items-center gap-2">
            {index > 0 && (
              <button onClick={() => setIndex((i) => i - 1)} className="btn-fantome text-[12.5px] px-2.5 py-1.5">
                Précédent
              </button>
            )}
            {!derniere && (
              <button onClick={() => onFermer(false)} className="text-[12px] text-txt2 hover:text-txt">
                Passer
              </button>
            )}
            <button onClick={suivant} className="btn-primaire text-[12.5px] px-3 py-1.5">
              {derniere ? "C'est parti" : "Suivant"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Voile({ style, onClick }) {
  return (
    // Le voile est décoratif : il assombrit ce qui n'est pas désigné. Il est
    // retiré de l'arbre d'accessibilité, car le clic dessus n'est qu'un
    // raccourci à la souris — la visite se pilote depuis les boutons de la
    // bulle, seuls chemins garantis au clavier.
    <div
      onClick={onClick}
      aria-hidden="true"
      className="absolute bg-fond/70 backdrop-blur-[2px] transition-[top,left,width,height] duration-200"
      style={style}
    />
  );
}

/** Place la bulle là où elle ne recouvre pas ce qu'elle désigne. */
function positionner(zone) {
  if (typeof window === "undefined") return { top: 80, left: 24 };
  const { innerWidth: L, innerHeight: H } = window;

  if (!zone) {
    return {
      top: Math.max(24, H / 2 - 120),
      left: Math.max(12, L / 2 - LARGEUR_BULLE / 2),
    };
  }

  const borner = (v, max) => Math.max(12, Math.min(v, max));

  // À droite si l'élément est dans la moitié gauche — le cas de la barre
  // latérale, qui est aussi le plus fréquent.
  if (zone.gauche + zone.largeur < L * 0.45) {
    return {
      top: borner(zone.haut, H - 240),
      left: borner(zone.gauche + zone.largeur + 12, L - LARGEUR_BULLE - 12),
    };
  }
  // Sinon dessous, ou dessus s'il n'y a pas la place.
  const dessous = zone.haut + zone.hauteur + 12;
  return {
    top: dessous < H - 230 ? dessous : Math.max(12, zone.haut - 230),
    left: borner(zone.gauche + zone.largeur / 2 - LARGEUR_BULLE / 2, L - LARGEUR_BULLE - 12),
  };
}

const CSS_VISITE = `
@keyframes visite-halo {
  0%, 100% { box-shadow: 0 0 0 0 rgba(59,130,246,.45); }
  50%      { box-shadow: 0 0 0 7px rgba(59,130,246,0); }
}
.visite-halo { animation: visite-halo 1.9s ease-out infinite; }
@keyframes visite-entree {
  from { opacity: 0; transform: translateY(8px) scale(.98); }
  to   { opacity: 1; transform: none; }
}
.visite-entree { animation: visite-entree .22s ease-out; }
`;
