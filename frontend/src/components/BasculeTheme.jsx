import { useTheme } from "@/lib/theme";

/** Bascule entre le thème sombre et le thème clair. */
export default function BasculeTheme({ compact = false }) {
  const { theme, basculer } = useTheme();
  const sombre = theme === "dark";

  return (
    <button
      onClick={basculer}
      aria-label={sombre ? "Passer au thème clair" : "Passer au thème sombre"}
      title={sombre ? "Thème clair" : "Thème sombre"}
      className={
        compact
          ? "w-9 h-9 grid place-items-center rounded-[10px] border border-bordure text-txt2 hover:text-txt hover:border-accent transition-colors"
          : "inline-flex items-center gap-2 rounded-[10px] border border-bordure px-3 py-2 text-xs text-txt2 hover:text-txt hover:border-accent transition-colors"
      }
    >
      {sombre ? <IconeSoleil /> : <IconeLune />}
      {!compact && <span>{sombre ? "Thème clair" : "Thème sombre"}</span>}
    </button>
  );
}

function IconeSoleil() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  );
}

function IconeLune() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </svg>
  );
}
