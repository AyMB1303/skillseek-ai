/** Gestion du thème d'affichage : sombre (défaut) ou clair.
 *
 *  Le choix de l'utilisateur est conservé d'une session à l'autre. En
 *  l'absence de choix explicite, la préférence déclarée par le système
 *  d'exploitation est respectée.
 */
import { createContext, useContext, useEffect, useState, useCallback } from "react";

const CLE = "skillseek_theme";
const ContexteTheme = createContext(null);

export function FournisseurTheme({ children }) {
  // Le thème réel est appliqué par le script de _document.jsx avant le premier
  // rendu ; on le relit ici pour synchroniser l'état de React.
  const [theme, setTheme] = useState("dark");

  useEffect(() => {
    const applique = document.documentElement.getAttribute("data-theme");
    if (applique) setTheme(applique);
  }, []);

  const changer = useCallback((nouveau) => {
    setTheme(nouveau);
    document.documentElement.setAttribute("data-theme", nouveau);
    try {
      localStorage.setItem(CLE, nouveau);
    } catch {
      /* navigation privée : le thème reste valable pour la session */
    }
  }, []);

  const basculer = useCallback(
    () => changer(theme === "dark" ? "light" : "dark"),
    [theme, changer]
  );

  return (
    <ContexteTheme.Provider value={{ theme, changer, basculer }}>
      {children}
    </ContexteTheme.Provider>
  );
}

export const useTheme = () => useContext(ContexteTheme);
