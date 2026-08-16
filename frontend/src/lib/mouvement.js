/**
 * Primitives d'animation communes.
 *
 * Trois règles gouvernent tout ce fichier.
 *
 * **L'animation ne porte jamais l'information.** Un chiffre qui s'incrémente
 * finit toujours sur sa valeur exacte, et cette valeur est écrite dans le DOM
 * dès le premier rendu pour un lecteur d'écran. Couper le mouvement ne doit
 * rien retirer à la compréhension.
 *
 * **Le réglage système fait autorité.** `prefers-reduced-motion` n'est pas une
 * option décorative : il est demandé par des personnes que le mouvement rend
 * malades. Ici, il court-circuite l'animation d'un seul endroit plutôt que
 * d'être réimplémenté dans chaque composant.
 *
 * **Rien ne s'anime hors de l'écran.** Les animations d'entrée attendent que
 * l'élément soit visible ; sinon le recruteur qui fait défiler une liste
 * arrive sur des compteurs déjà terminés.
 */
import { useEffect, useRef, useState } from "react";

/** Vrai si le système demande à limiter les animations. */
export function useMouvementReduit() {
  const [reduit, setReduit] = useState(false);

  useEffect(() => {
    const requete = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduit(requete.matches);
    const suivre = (e) => setReduit(e.matches);
    requete.addEventListener("change", suivre);
    return () => requete.removeEventListener("change", suivre);
  }, []);

  return reduit;
}

/** Décélération : rapide au départ, posée à l'arrivée. */
const adoucir = (t) => 1 - Math.pow(1 - t, 3);

/**
 * Compte de 0 jusqu'à `cible`.
 *
 * Le pas suit le temps réel et non un nombre d'images : la durée reste la même
 * sur un écran à 60 Hz et sur un écran à 144 Hz.
 */
export function useCompteur(cible, { duree = 900, actif = true } = {}) {
  const reduit = useMouvementReduit();
  const [valeur, setValeur] = useState(cible ?? 0);
  const precedent = useRef(cible ?? 0);

  useEffect(() => {
    if (cible == null) return;
    if (reduit || !actif) {
      setValeur(cible);
      precedent.current = cible;
      return;
    }

    const depart = precedent.current;
    const debut = performance.now();
    let image;

    const avancer = (instant) => {
      const t = Math.min(1, (instant - debut) / duree);
      setValeur(Math.round(depart + (cible - depart) * adoucir(t)));
      if (t < 1) image = requestAnimationFrame(avancer);
      else precedent.current = cible;
    };

    image = requestAnimationFrame(avancer);
    return () => cancelAnimationFrame(image);
  }, [cible, duree, reduit, actif]);

  return valeur;
}

/**
 * Signale qu'un élément est entré dans la fenêtre, une seule fois.
 *
 * Renvoie `[ref, visible]`. Sans `IntersectionObserver` — navigateur ancien,
 * rendu serveur — l'élément est considéré visible : mieux vaut une animation
 * manquée qu'un contenu qui n'apparaît jamais.
 */
export function useEntreeEnVue({ marge = "0px 0px -10% 0px" } = {}) {
  const cible = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const noeud = cible.current;
    if (!noeud || typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const observateur = new IntersectionObserver(
      ([entree]) => {
        if (entree.isIntersecting) {
          setVisible(true);
          observateur.disconnect();
        }
      },
      { rootMargin: marge, threshold: 0.15 }
    );
    observateur.observe(noeud);
    return () => observateur.disconnect();
  }, [marge]);

  return [cible, visible];
}

/** Délai d'apparition d'un élément dans une série, borné pour rester bref. */
export function retard(index, pas = 60, plafond = 420) {
  return `${Math.min(index * pas, plafond)}ms`;
}
