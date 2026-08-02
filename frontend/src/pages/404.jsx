import Link from "next/link";
import { useAuth, ACCUEIL_PAR_ROLE } from "@/lib/auth";

export default function PageIntrouvable() {
  const { utilisateur } = useAuth();
  const retour = utilisateur ? ACCUEIL_PAR_ROLE[utilisateur.role] || "/" : "/connexion";

  return (
    <div className="min-h-screen grid place-items-center p-4 text-center">
      <div className="space-y-4">
        <p className="text-6xl font-bold text-bordure">404</p>
        <h1 className="text-xl font-semibold">Page introuvable</h1>
        <p className="text-sm text-txt2 max-w-sm">
          La page que vous cherchez n'existe pas ou a été déplacée.
        </p>
        <Link href={retour} className="btn-primaire inline-flex">Retour à l'accueil</Link>
      </div>
    </div>
  );
}
