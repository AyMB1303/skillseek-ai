/** Design system SkillSeek AI — thème sombre. */
module.exports = {
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        fond: "#0B1220",        // fond principal
        surface: "#111A2E",     // cartes
        surface2: "#0D1526",    // sidebar / header
        bordure: "#1E2A44",
        accent: "#3B82F6",      // bleu primaire
        cyan: "#22D3EE",        // accent IA
        succes: "#34D399",
        alerte: "#F59E0B",
        erreur: "#F87171",
        txt: "#E5EAF3",
        txt2: "#8B98B8",
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
