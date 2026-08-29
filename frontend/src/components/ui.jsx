/** Composants d'interface réutilisables : toasts, états, badges, modales. */
import { createContext, useContext, useState, useCallback, useEffect } from "react";

/* ---------------------------- Toasts ---------------------------- */

const ContexteToast = createContext(null);

export function FournisseurToast({ children }) {
  const [toasts, setToasts] = useState([]);

  const retirer = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), []);

  /** annuler : callback optionnel — affiche un bouton « Annuler » pendant 5 s. */
  const notifier = useCallback(
    (message, { type = "succes", annuler } = {}) => {
      const id = Date.now() + Math.random();
      setToasts((t) => [...t, { id, message, type, annuler }]);
      setTimeout(() => retirer(id), 5000);
      return id;
    },
    [retirer]
  );

  return (
    <ContexteToast.Provider value={{ notifier }}>
      {children}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 w-[340px]">
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={`carte animate-pop flex items-start gap-3 p-3.5 shadow-2xl border-l-4 ${
              t.type === "erreur" ? "border-l-erreur" : "border-l-succes"
            }`}
          >
            <p className="flex-1 text-sm">{t.message}</p>
            {t.annuler && (
              <button
                onClick={() => {
                  t.annuler();
                  retirer(t.id);
                }}
                className="text-xs font-semibold text-accent hover:text-cyan"
              >
                Annuler
              </button>
            )}
            <button onClick={() => retirer(t.id)} aria-label="Fermer" className="text-txt2 hover:text-txt">
              ×
            </button>
          </div>
        ))}
      </div>
    </ContexteToast.Provider>
  );
}

export const useToast = () => useContext(ContexteToast);

/* ------------------------- États de page ------------------------- */

export function Chargement({ lignes = 3 }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Chargement en cours">
      {Array.from({ length: lignes }).map((_, i) => (
        <div key={i} className="h-16 rounded-xl2 bg-surface animate-pulse" />
      ))}
    </div>
  );
}

export function EtatVide({ titre, description, action }) {
  return (
    <div className="carte flex flex-col items-center justify-center gap-3 py-14 px-6 text-center">
      <div className="w-12 h-12 rounded-full bg-bordure/50 grid place-items-center text-2xl">·</div>
      <h3 className="font-semibold">{titre}</h3>
      {description && <p className="text-sm text-txt2 max-w-sm">{description}</p>}
      {action}
    </div>
  );
}

export function EtatErreur({ message, onReessayer }) {
  return (
    <div className="carte border-erreur/40 p-6 text-center space-y-3">
      <p className="text-sm text-erreur">{message}</p>
      {onReessayer && (
        <button onClick={onReessayer} className="btn-secondaire">
          Réessayer
        </button>
      )}
    </div>
  );
}

/* --------------------------- Badges --------------------------- */

const STATUTS = {
  received: { libelle: "Reçue", classe: "bg-bordure/50 text-txt2" },
  under_review: { libelle: "En étude", classe: "bg-accent/15 text-accent" },
  shortlisted: { libelle: "Présélectionné", classe: "bg-cyan/15 text-cyan" },
  interview: { libelle: "Entretien", classe: "bg-alerte/15 text-alerte" },
  hired: { libelle: "Recruté", classe: "bg-succes/15 text-succes" },
  rejected: { libelle: "Non retenu", classe: "bg-bordure/50 text-txt2" },
};

export function BadgeStatut({ statut }) {
  const s = STATUTS[statut] || STATUTS.received;
  return <span className={`chip ${s.classe}`}>{s.libelle}</span>;
}

export { STATUTS };

/* --------------------------- Modale --------------------------- */

export function Modale({ ouverte, onFermer, titre, children, actions }) {
  useEffect(() => {
    if (!ouverte) return;
    const onKey = (e) => e.key === "Escape" && onFermer();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [ouverte, onFermer]);

  if (!ouverte) return null;
  return (
    <div className="fixed inset-0 z-40 grid place-items-center p-4">
      {/* Le fond est décoratif : il est retiré de l'arbre d'accessibilité.
          Le clic dessus est un raccourci à la souris, jamais le seul moyen de
          fermer — la touche Échap et le bouton « Fermer » restent les chemins
          garantis. Séparer le fond du dialogue évite aussi d'avoir à arrêter
          la propagation du clic, et surtout de poser un gestionnaire de clic
          sur l'élément qui porte role="dialog", ce qui rendait le dialogue
          lui-même faussement interactif pour les technologies d'assistance. */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onFermer}
        aria-hidden="true"
      />
      <div
        className="carte w-full max-w-lg animate-pop relative"
        role="dialog"
        aria-modal="true"
        aria-label={titre}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-bordure">
          <h2 className="font-semibold">{titre}</h2>
          <button onClick={onFermer} aria-label="Fermer" className="text-txt2 hover:text-txt text-xl leading-none">
            ×
          </button>
        </div>
        <div className="p-5">{children}</div>
        {actions && <div className="flex justify-end gap-2 px-5 py-4 border-t border-bordure">{actions}</div>}
      </div>
    </div>
  );
}

/* --------------------------- Drawer --------------------------- */

export function Drawer({ ouvert, onFermer, titre, children }) {
  useEffect(() => {
    if (!ouvert) return;
    const onKey = (e) => e.key === "Escape" && onFermer();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [ouvert, onFermer]);

  if (!ouvert) return null;
  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      {/* Même principe que la modale : fond décoratif, retiré de l'arbre
          d'accessibilité, et panneau séparé qui porte seul le rôle. */}
      <div className="absolute inset-0 bg-black/50" onClick={onFermer} aria-hidden="true" />
      <aside
        className="w-full max-w-md bg-surface2 border-l border-bordure h-full overflow-y-auto animate-slideIn relative"
        role="dialog"
        aria-label={titre}
      >
        <div className="sticky top-0 bg-surface2 flex items-center justify-between px-5 py-4 border-b border-bordure">
          <h2 className="font-semibold">{titre}</h2>
          <button onClick={onFermer} aria-label="Fermer" className="text-txt2 hover:text-txt text-xl leading-none">
            ×
          </button>
        </div>
        <div className="p-5">{children}</div>
      </aside>
    </div>
  );
}
