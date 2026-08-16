/** Design system SkillSeek AI.
 *
 *  Les couleurs sont définies par des variables CSS (globals.css), ce qui
 *  permet aux thèmes sombre et clair de partager exactement le même code de
 *  composants. La syntaxe `rgb(var(--x) / <alpha-value>)` conserve le support
 *  des opacités Tailwind (bg-accent/15, text-succes/50, etc.).
 */
const couleur = (variable) => `rgb(var(${variable}) / <alpha-value>)`;

module.exports = {
  content: ["./src/**/*.{js,jsx}"],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        fond: couleur("--c-fond"),           // fond principal
        surface: couleur("--c-surface"),     // cartes
        surface2: couleur("--c-surface2"),   // sidebar, header
        bordure: couleur("--c-bordure"),
        accent: couleur("--c-accent"),       // bleu primaire
        cyan: couleur("--c-cyan"),           // accent analyse
        succes: couleur("--c-succes"),
        alerte: couleur("--c-alerte"),
        erreur: couleur("--c-erreur"),
        txt: couleur("--c-txt"),             // texte principal
        txt2: couleur("--c-txt2"),           // texte secondaire
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: { xl2: "12px" },
      keyframes: {
        pop: { "0%": { opacity: 0, transform: "translateY(-6px)" }, "100%": { opacity: 1, transform: "translateY(0)" } },
        slideIn: { "0%": { transform: "translateX(100%)" }, "100%": { transform: "translateX(0)" } },
      },
      animation: {
        pop: "pop 160ms ease-out",
        slideIn: "slideIn 200ms ease-out",
      },
    },
  },
  plugins: [],
};
