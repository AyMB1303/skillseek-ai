import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function Connexion() {
  const { connexion } = useAuth();
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [visible, setVisible] = useState(false);
  const [erreur, setErreur] = useState("");
  const [envoi, setEnvoi] = useState(false);

  const soumettre = async (e) => {
    e.preventDefault();
    setErreur("");
    setEnvoi(true);
    try {
      await connexion(email, motDePasse);
    } catch (err) {
      setErreur(err.message || "Identifiants invalides.");
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <div className="min-h-screen grid place-items-center p-4 bg-gradient-to-br from-fond to-surface2">
      <div className="w-full max-w-[400px]">
        <div className="flex items-center justify-center gap-2.5 mb-7">
          <div className="w-10 h-10 rounded-xl2 bg-gradient-to-br from-accent to-cyan grid place-items-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0B1220" strokeWidth="2.4" strokeLinecap="round">
              <circle cx="10.5" cy="10.5" r="6" />
              <line x1="15" y1="15" x2="20" y2="20" />
            </svg>
          </div>
          <span className="font-bold text-lg">SkillSeek <span className="text-cyan">AI</span></span>
        </div>

        <form onSubmit={soumettre} className="carte p-6 space-y-4" noValidate>
          <div>
            <h1 className="text-xl font-bold">Bon retour</h1>
            <p className="text-sm text-txt2 mt-1">Connectez-vous à votre espace.</p>
          </div>

          {erreur && (
            <div role="alert" className="rounded-[10px] border border-erreur/40 bg-erreur/10 px-3.5 py-2.5 text-sm text-erreur">
              {erreur}
            </div>
          )}

          <div>
            <label htmlFor="email" className="etiquette">Adresse email</label>
            <input
              id="email" type="email" required autoComplete="email" className="champ"
              value={email} onChange={(e) => setEmail(e.target.value)} placeholder="vous@exemple.com"
            />
          </div>

          <div>
            <label htmlFor="mdp" className="etiquette">Mot de passe</label>
            <div className="relative">
              <input
                id="mdp" type={visible ? "text" : "password"} required autoComplete="current-password"
                className="champ pr-11" value={motDePasse} onChange={(e) => setMotDePasse(e.target.value)}
                placeholder="••••••••"
              />
              <button
                type="button" onClick={() => setVisible(!visible)}
                aria-label={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                className="absolute right-1 top-1/2 -translate-y-1/2 w-9 h-9 grid place-items-center text-txt2 hover:text-txt"
              >
                {visible ? "🙈" : "👁"}
              </button>
            </div>
          </div>

          <button type="submit" disabled={envoi} className="btn-primaire w-full">
            {envoi ? "Connexion…" : "Se connecter"}
          </button>

          <p className="text-sm text-txt2 text-center">
            Pas encore de compte ? <Link href="/inscription" className="text-accent hover:text-cyan">Créer un compte</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
