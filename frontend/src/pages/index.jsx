import { useEffect } from "react";
import { useRouter } from "next/router";
import { useAuth, ACCUEIL_PAR_ROLE } from "@/lib/auth";

export default function Accueil() {
  const { utilisateur, chargement } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (chargement) return;
    router.replace(utilisateur ? ACCUEIL_PAR_ROLE[utilisateur.role] || "/connexion" : "/connexion");
  }, [utilisateur, chargement, router]);

  return <div className="min-h-screen grid place-items-center text-txt2 text-sm">Chargement…</div>;
}
