/** Layout connecté : sidebar par rôle, header avec recherche, notifications et menu profil. */
import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

const NAV = {
  admin: [
    { href: "/admin/utilisateurs", libelle: "Utilisateurs", icone: IconeUsers },
    { href: "/admin/roles", libelle: "Rôles & permissions", icone: IconeShield },
    { href: "/profil", libelle: "Mon profil", icone: IconeUser },
  ],
  recruiter: [
    { href: "/dashboard", libelle: "Dashboard", icone: IconeGrid },
    { href: "/offres/gestion", libelle: "Mes offres", icone: IconeBriefcase },
    { href: "/candidatures", libelle: "Candidatures", icone: IconeFile, compteur: true },
    { href: "/assistant", libelle: "Assistant RH", icone: IconeChat },
    { href: "/profil", libelle: "Mon profil", icone: IconeUser },
  ],
  candidate: [
    { href: "/offres", libelle: "Offres d'emploi", icone: IconeBriefcase },
    { href: "/mes-candidatures", libelle: "Mes candidatures", icone: IconeFile },
    { href: "/profil", libelle: "Mon profil", icone: IconeUser },
  ],
};

export default function Layout({ children, titre, compteurCandidatures }) {
  const { utilisateur, deconnexion } = useAuth();
  const router = useRouter();
  const [replie, setReplie] = useState(false);
  const [menuOuvert, setMenuOuvert] = useState(false);
  const [notifOuvert, setNotifOuvert] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const champRecherche = useRef(null);

  // Notifications persistées en base, propres à l'utilisateur connecté.
  const chargerNotifications = useCallback(async () => {
    if (!utilisateur) return;
    try {
      const d = await api.notifications();
      setNotifications(d.notifications);
    } catch {
      /* silencieux : une notification indisponible ne doit pas bloquer la page */
    }
  }, [utilisateur]);

  useEffect(() => {
    chargerNotifications();
    // Rafraîchissement périodique : les événements viennent d'autres utilisateurs.
    const timer = setInterval(chargerNotifications, 30000);
    return () => clearInterval(timer);
  }, [chargerNotifications]);

  const marquerLue = async (notif) => {
    setNotifications((l) => l.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n)));
    try {
      await api.marquerLue(notif.id);
    } catch {
      /* l'état local reste cohérent au prochain rafraîchissement */
    }
  };

  const marquerToutesLues = async () => {
    setNotifications((l) => l.map((n) => ({ ...n, is_read: true })));
    try {
      await api.marquerToutesLues();
    } catch {
      /* idem */
    }
  };

  // Raccourci ⌘K / Ctrl+K vers la recherche
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        champRecherche.current?.focus();
      }
      if (e.key === "Escape") {
        setMenuOuvert(false);
        setNotifOuvert(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const liens = NAV[utilisateur?.role] || [];
  const nonLues = useMemo(() => notifications.filter((n) => !n.is_read), [notifications]);
  const initiales = (utilisateur?.full_name || "?")
    .split(" ")
    .map((m) => m[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="flex min-h-screen">
      {/* ---------------- Sidebar ---------------- */}
      <aside
        className={`${replie ? "w-[72px]" : "w-[236px]"} shrink-0 bg-surface2 border-r border-bordure
                    flex flex-col p-3.5 gap-1.5 sticky top-0 h-screen transition-[width] duration-150`}
      >
        <div className="flex items-center gap-2.5 px-2.5 pt-1.5 pb-5">
          <div className="w-[34px] h-[34px] rounded-[10px] bg-gradient-to-br from-accent to-cyan grid place-items-center shrink-0">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0B1220" strokeWidth="2.4" strokeLinecap="round">
              <circle cx="10.5" cy="10.5" r="6" />
              <line x1="15" y1="15" x2="20" y2="20" />
            </svg>
          </div>
          {!replie && (
            <span className="font-bold text-base tracking-tight whitespace-nowrap">
              SkillSeek <span className="text-cyan">AI</span>
            </span>
          )}
        </div>

        <nav className="flex flex-col gap-1">
          {liens.map((l) => {
            const actif = router.pathname === l.href || router.pathname.startsWith(l.href + "/");
            const Icone = l.icone;
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={actif ? "page" : undefined}
                title={replie ? l.libelle : undefined}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-[10px] text-sm transition-colors ${
                  actif
                    ? "bg-accent/15 border border-accent/25 text-txt font-semibold"
                    : "text-txt2 hover:bg-surface hover:text-txt font-medium"
                }`}
              >
                <Icone actif={actif} />
                {!replie && <span className="whitespace-nowrap flex-1">{l.libelle}</span>}
                {!replie && l.compteur && compteurCandidatures > 0 && (
                  <span className="bg-accent text-white text-[11px] font-semibold rounded-full px-2 py-px">
                    {compteurCandidatures}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <button
          onClick={() => setReplie(!replie)}
          className="mt-auto text-txt2 hover:text-txt text-xs px-3 py-2 text-left"
          aria-label={replie ? "Déplier le menu" : "Replier le menu"}
        >
          {replie ? "»" : "« Replier"}
        </button>

        <div className="border-t border-bordure pt-3.5 flex items-center gap-2.5 px-1.5">
          <div className="w-[34px] h-[34px] rounded-full bg-bordure text-cyan grid place-items-center text-xs font-bold shrink-0">
            {initiales}
          </div>
          {!replie && (
            <div className="min-w-0">
              <div className="text-[13px] font-semibold truncate">{utilisateur?.full_name}</div>
              <div className="text-[11.5px] text-txt2 capitalize">{libelleRole(utilisateur?.role)}</div>
            </div>
          )}
        </div>
      </aside>

      {/* ---------------- Contenu ---------------- */}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-20 bg-surface2/95 backdrop-blur border-b border-bordure px-6 py-3 flex items-center gap-4">
          <h1 className="text-[15px] font-semibold shrink-0">{titre}</h1>

          <div className="flex-1 max-w-md ml-auto flex items-center gap-2 bg-fond border border-bordure rounded-[10px] px-3 py-2">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8B98B8" strokeWidth="2">
              <circle cx="11" cy="11" r="7" />
              <line x1="16" y1="16" x2="21" y2="21" />
            </svg>
            <input
              ref={champRecherche}
              type="search"
              placeholder="Rechercher…"
              className="bg-transparent border-0 outline-none text-[13.5px] w-full"
              onChange={(e) => router.push({ pathname: "/recherche", query: { q: e.target.value } }, undefined, { shallow: true })}
              aria-label="Recherche globale"
            />
            <kbd className="text-[11px] text-txt2 border border-bordure rounded px-1.5">⌘K</kbd>
          </div>

          {/* Notifications */}
          <div className="relative">
            <button
              onClick={() => { setNotifOuvert(!notifOuvert); setMenuOuvert(false); }}
              className={`relative w-9 h-9 grid place-items-center rounded-[10px] border transition-colors ${
                notifOuvert ? "border-accent" : "border-bordure"
              }`}
              aria-label={`Notifications${nonLues.length ? ` (${nonLues.length} non lues)` : ""}`}
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#8B98B8" strokeWidth="2">
                <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
                <path d="M13.7 21a2 2 0 0 1-3.4 0" />
              </svg>
              {nonLues.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-erreur text-white text-[10px] font-bold rounded-full w-4 h-4 grid place-items-center">
                  {nonLues.length}
                </span>
              )}
            </button>

            {notifOuvert && (
              <div className="absolute top-11 right-0 w-[320px] carte bg-surface2 shadow-2xl animate-pop overflow-hidden z-30">
                <div className="flex items-center justify-between px-4 py-3 border-b border-bordure">
                  <span className="text-sm font-semibold">Notifications</span>
                  {nonLues.length > 0 && (
                    <button onClick={marquerToutesLues} className="text-xs text-accent hover:text-cyan">
                      Tout marquer comme lu
                    </button>
                  )}
                </div>
                {notifications.length === 0 ? (
                  <p className="px-4 py-6 text-sm text-txt2 text-center">
                    Aucune notification pour le moment.
                  </p>
                ) : (
                  <div className="max-h-[380px] overflow-y-auto">
                    {notifications.map((n) => (
                      <Link
                        key={n.id}
                        href={n.link || "#"}
                        onClick={() => {
                          marquerLue(n);
                          setNotifOuvert(false);
                        }}
                        className={`flex gap-3 px-4 py-3 border-b border-bordure last:border-0 hover:bg-surface transition-colors ${
                          n.is_read ? "opacity-55" : ""
                        }`}
                      >
                        <span
                          className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
                          style={{ background: n.is_read ? "transparent" : COULEUR_NOTIF[n.type] || "#3B82F6" }}
                        />
                        <div className="min-w-0">
                          <p className="text-[13px] leading-snug">{n.message}</p>
                          <p className="text-[11px] text-txt2 mt-1">{ilYA(n.created_at)}</p>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Menu profil */}
          <div className="relative">
            <button
              onClick={() => { setMenuOuvert(!menuOuvert); setNotifOuvert(false); }}
              className="w-9 h-9 rounded-full bg-bordure text-cyan grid place-items-center text-xs font-bold"
              aria-label="Menu utilisateur"
              aria-expanded={menuOuvert}
            >
              {initiales}
            </button>
            {menuOuvert && (
              <div className="absolute top-11 right-0 w-[210px] carte bg-surface2 shadow-2xl animate-pop overflow-hidden z-30">
                <div className="px-4 py-3 border-b border-bordure">
                  <div className="text-[13px] font-semibold">{utilisateur?.full_name}</div>
                  <div className="text-[11.5px] text-txt2 truncate">{utilisateur?.email}</div>
                </div>
                <Link href="/profil" onClick={() => setMenuOuvert(false)} className="block px-4 py-2.5 text-[13px] hover:bg-surface">
                  Mon profil
                </Link>
                <button
                  onClick={deconnexion}
                  className="w-full text-left px-4 py-2.5 text-[13px] text-erreur hover:bg-surface"
                >
                  Se déconnecter
                </button>
              </div>
            )}
          </div>
        </header>

        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}

const libelleRole = (r) => ({ admin: "Administrateur", recruiter: "Recruteur", candidate: "Candidat" }[r] || "");

// Couleur du point selon le type d'événement
const COULEUR_NOTIF = {
  candidature_recue: "#3B82F6",
  statut_change: "#34D399",
  compte_cree: "#22D3EE",
  permissions_modifiees: "#F59E0B",
  offre_publiee: "#8B98B8",
};

/** Formatage relatif de la date (« il y a 5 min »). */
function ilYA(iso) {
  const minutes = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const heures = Math.floor(minutes / 60);
  if (heures < 24) return `il y a ${heures} h`;
  const jours = Math.floor(heures / 24);
  return jours === 1 ? "hier" : `il y a ${jours} jours`;
}

/* ------------------------------ Icônes ------------------------------ */
const props = (actif) => ({
  width: 17, height: 17, viewBox: "0 0 24 24", fill: "none",
  stroke: actif ? "#3B82F6" : "currentColor", strokeWidth: 2, strokeLinecap: "round",
});
function IconeGrid({ actif }) { return <svg {...props(actif)}><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>; }
function IconeBriefcase({ actif }) { return <svg {...props(actif)}><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>; }
function IconeFile({ actif }) { return <svg {...props(actif)}><path d="M14 3v5h5"/><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/></svg>; }
function IconeChat({ actif }) { return <svg {...props(actif)}><path d="M21 12a8 8 0 0 1-8 8H4l2-3a8 8 0 1 1 15-5z"/></svg>; }
function IconeUser({ actif }) { return <svg {...props(actif)}><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5"/></svg>; }
function IconeUsers({ actif }) { return <svg {...props(actif)}><circle cx="9" cy="8" r="3.5"/><path d="M2 21c0-3.5 3.1-5.5 7-5.5s7 2 7 5.5"/><path d="M17 11a3 3 0 1 0 0-6"/></svg>; }
function IconeShield({ actif }) { return <svg {...props(actif)}><path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/></svg>; }
