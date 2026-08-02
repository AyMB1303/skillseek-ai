import { useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui";

// Mêmes règles que la validation serveur (auth.py) : cohérence garantie.
const CRITERES = [
  { cle: "longueur", libelle: "8 caractères minimum", test: (v) => v.length >= 8 },
  { cle: "majuscule", libelle: "Une majuscule", test: (v) => /[A-Z]/.test(v) },
  { cle: "minuscule", libelle: "Une minuscule", test: (v) => /[a-z]/.test(v) },
  { cle: "chiffre", libelle: "Un chiffre", test: (v) => /\d/.test(v) },
];

export default function Inscription() {
  const router = useRouter();
  const { notifier } = useToast();
  const [f, setF] = useState({ full_name: "", email: "", password: "", confirmation: "" });
  const [consent, setConsent] = useState(false);
  const [erreurs, setErreurs] = useState({});
  const [envoi, setEnvoi] = useState(false);

  const maj = (champ) => (e) => setF({ ...f, [champ]: e.target.value });

  const valides = useMemo(() => CRITERES.map((c) => ({ ...c, ok: c.test(f.password) })), [f.password]);
  const force = valides.filter((c) => c.ok).length;

  const valider = () => {
    const e = {};
    if (f.full_name.trim().length < 3) e.full_name = "Nom complet requis (3 caractères minimum).";
    if (!/^[\w.+-]+@[\w-]+\.[\w.-]+$/.test(f.email)) e.email = "Adresse email invalide.";
    if (force < 4) e.password = "Le mot de passe ne remplit pas tous les critères.";
    if (f.password !== f.confirmation) e.confirmation = "Les mots de passe ne correspondent pas.";
    if (!consent) e.consent = "Votre consentement est nécessaire pour postuler.";
    setErreurs(e);
    return Object.keys(e).length === 0;
  };

  const soumettre = async (ev) => {
    ev.preventDefault();
    if (!valider()) return;
    setEnvoi(true);
    try {
      await api.inscription({ full_name: f.full_name, email: f.email, password: f.password });
      notifier("Compte créé. Vous pouvez vous connecter.");
      router.push("/connexion");
    } catch (err) {
      setErreurs(err.details || { general: err.message });
    } finally {
      setEnvoi(false);
    }
  };

  const couleurForce = ["bg-bordure", "bg-erreur", "bg-alerte", "bg-alerte", "bg-succes"][force];

  return (
    <div className="min-h-screen grid place-items-center p-4 bg-gradient-to-br from-fond to-surface2">
      <form onSubmit={soumettre} className="carte w-full max-w-[440px] p-6 space-y-4" noValidate>
        <div>
          <h1 className="text-xl font-bold">Créer un compte</h1>
          <p className="text-sm text-txt2 mt-1">Déposez vos candidatures en quelques clics.</p>
        </div>

        {erreurs.general && (
          <div role="alert" className="rounded-[10px] border border-erreur/40 bg-erreur/10 px-3.5 py-2.5 text-sm text-erreur">
            {erreurs.general}
          </div>
        )}

        <Champ id="nom" label="Nom complet" value={f.full_name} onChange={maj("full_name")} erreur={erreurs.full_name} autoComplete="name" />
        <Champ id="email" label="Adresse email" type="email" value={f.email} onChange={maj("email")} erreur={erreurs.email} autoComplete="email" />

        <div>
          <label htmlFor="mdp" className="etiquette">Mot de passe</label>
          <input id="mdp" type="password" className="champ" value={f.password} onChange={maj("password")} autoComplete="new-password" />
          <div className="mt-2 h-1 rounded-full bg-bordure overflow-hidden">
            <div className={`h-full transition-all ${couleurForce}`} style={{ width: `${(force / 4) * 100}%` }} />
          </div>
          <ul className="mt-2 grid grid-cols-2 gap-1">
            {valides.map((c) => (
              <li key={c.cle} className={`text-[11.5px] flex items-center gap-1.5 ${c.ok ? "text-succes" : "text-txt2"}`}>
                <span>{c.ok ? "✓" : "○"}</span> {c.libelle}
              </li>
            ))}
          </ul>
          {erreurs.password && <p className="text-xs text-erreur mt-1.5">{erreurs.password}</p>}
        </div>

        <Champ id="conf" label="Confirmer le mot de passe" type="password" value={f.confirmation} onChange={maj("confirmation")} erreur={erreurs.confirmation} autoComplete="new-password" />

        <label className="flex items-start gap-2.5 cursor-pointer">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 accent-accent w-4 h-4" />
          <span className="text-[12.5px] text-txt2 leading-snug">
            Je consens à l'analyse automatisée de mon CV par le système. La décision finale reste prise par un recruteur.
          </span>
        </label>
        {erreurs.consent && <p className="text-xs text-erreur -mt-2">{erreurs.consent}</p>}

        <button type="submit" disabled={envoi} className="btn-primaire w-full">
          {envoi ? "Création…" : "Créer mon compte"}
        </button>

        <p className="text-sm text-txt2 text-center">
          Déjà inscrit ? <Link href="/connexion" className="text-accent hover:text-cyan">Se connecter</Link>
        </p>
      </form>
    </div>
  );
}

function Champ({ id, label, erreur, ...rest }) {
  return (
    <div>
      <label htmlFor={id} className="etiquette">{label}</label>
      <input id={id} className={`champ ${erreur ? "border-erreur" : ""}`} aria-invalid={!!erreur} {...rest} />
      {erreur && <p className="text-xs text-erreur mt-1.5">{erreur}</p>}
    </div>
  );
}
