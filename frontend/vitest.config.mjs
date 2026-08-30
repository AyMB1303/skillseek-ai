// Configuration des tests de l'interface.
//
// Le périmètre est volontairement étroit : les fonctions pures de src/lib.
// Tester le rendu des composants demanderait un environnement de navigateur
// simulé et des tests bien plus fragiles, pour une valeur moindre — ce sont
// les règles, et non le balisage, qui décident du comportement.
import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    include: ["src/**/*.test.js"],
    coverage: {
      provider: "v8",
      // Format lcov : c'est celui que SonarCloud sait lire.
      reporter: ["text", "lcov"],
      reportsDirectory: "coverage",
      include: ["src/lib/regles.js"],
    },
  },
});
