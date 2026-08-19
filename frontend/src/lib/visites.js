/**
 * Contenu des visites guidées, par rôle.
 *
 * Les trois rôles n'entrent pas dans la plateforme par la même porte, et une
 * visite unique servirait mal les trois. Le candidat a besoin de savoir où
 * postuler et ce que devient son dossier ; le recruteur, de comprendre que le
 * classement est une proposition et non un verdict ; l'administrateur, de
 * repérer ce qui attend sa décision.
 *
 * Les cibles sont des attributs `data-visite` posés dans le Layout plutôt que
 * des sélecteurs de classes. Une classe change au premier ajustement de style
 * et casse la visite en silence ; un attribut nommé dit explicitement qu'un
 * élément est référencé ailleurs.
 *
 * `VERSION` invalide les visites déjà vues : si une refonte ajoute un écran,
 * l'incrémenter suffit à la reproposer à tout le monde.
 */
export const VERSION = 2;

const ETAPE_PROFIL = {
  cible: '[data-visite="profil"]',
  titre: "Votre compte",
  texte:
    "Vos informations, le changement de mot de passe et la déconnexion se " +
    "trouvent ici. Vous pourrez aussi y relancer cette visite à tout moment.",
};

const ETAPE_THEME = {
  cible: '[data-visite="theme"]',
  titre: "Clair ou sombre",
  texte:
    "L'interface suit par défaut le réglage de votre système. Ce bouton force " +
    "l'un ou l'autre, et votre choix est conservé.",
};

export const VISITES = {
  candidate: [
    {
      cible: null,
      titre: "Bienvenue sur SkillSeek AI",
      texte:
        "Quelques secondes pour vous montrer où tout se trouve. Vous pouvez " +
        "interrompre à tout moment : la visite reste accessible depuis votre profil.",
    },
    {
      cible: '[data-visite="nav:/mon-profil-pro"]',
      titre: "Commencez par là",
      texte:
        "Indiquez ce que vous savez faire — quelques compétences, votre " +
        "expérience, votre diplôme. La plateforme classera alors les offres " +
        "selon votre profil et vous dira ce qu'il vous manque pour chacune. " +
        "Une minute, et vous cessez de postuler au hasard.",
    },
    {
      cible: '[data-visite="nav:/offres"]',
      titre: "Les offres d'emploi",
      texte:
        "Toutes les offres ouvertes sont ici. Chaque annonce indique les " +
        "compétences attendues, l'expérience demandée et le lieu, avant même " +
        "que vous ne postuliez.",
    },
    {
      cible: '[data-visite="nav:/mes-candidatures"]',
      titre: "Le suivi de vos candidatures",
      texte:
        "Une fois votre CV déposé, vous suivez son avancement ici : reçue, en " +
        "cours d'étude, entretien, décision. Vous êtes prévenu à chaque " +
        "changement, sans avoir à relancer l'entreprise.",
    },
    {
      cible: '[data-visite="nav:/profil"]',
      titre: "Votre CV et vos données",
      texte:
        "Votre CV se dépose depuis votre profil. Vous pouvez le consulter, le " +
        "télécharger ou le supprimer quand vous le souhaitez : vos données " +
        "restent les vôtres.",
    },
    {
      cible: '[data-visite="notifications"]',
      titre: "Vos notifications",
      texte:
        "Chaque étape franchie par votre dossier apparaît ici. Le compteur " +
        "rouge indique ce que vous n'avez pas encore lu.",
    },
    {
      cible: '[data-visite="recherche"]',
      titre: "La recherche",
      texte:
        "Un raccourci clavier — Ctrl K, ou ⌘K sur Mac — vous y amène depuis " +
        "n'importe quel écran.",
    },
    ETAPE_THEME,
    {
      cible: null,
      titre: "Un mot sur l'analyse de votre CV",
      texte:
        "Votre CV est lu automatiquement pour être comparé à l'offre, avec " +
        "votre accord explicite au moment du dépôt. Aucune décision n'est " +
        "prise sans un recruteur : le système propose, il ne tranche jamais.",
    },
  ],

  recruiter: [
    {
      cible: null,
      titre: "Bienvenue sur SkillSeek AI",
      texte:
        "Un tour rapide des écrans que vous utiliserez le plus. Vous pouvez " +
        "interrompre à tout moment et reprendre depuis votre profil.",
    },
    {
      cible: '[data-visite="nav:/offres/gestion"]',
      titre: "Vos offres",
      texte:
        "Publiez et modifiez vos annonces ici. Les compétences se saisissent " +
        "une par une et sont reconnues par le système : c'est ce qui permet de " +
        "les retrouver dans les CV.",
    },
    {
      cible: '[data-visite="nav:/candidatures"]',
      titre: "Les candidatures classées",
      texte:
        "Chaque dossier reçoit une note sur 100 et un motif. En dessous de 50, " +
        "la candidature est écartée du classement — jamais supprimée, et " +
        "toujours repêchable. Le classement est une proposition ; la décision " +
        "vous appartient.",
    },
    {
      cible: '[data-visite="nav:/pipeline"]',
      titre: "Le pipeline",
      texte:
        "La même liste vue par étape, à faire glisser d'une colonne à l'autre. " +
        "Pratique pour voir d'un coup d'œil où en est chaque recrutement.",
    },
    {
      cible: '[data-visite="nav:/signalements"]',
      titre: "Le contrôle des dossiers",
      texte:
        "Des anomalies sont relevées automatiquement sur les candidatures : " +
        "identité divergente, document dupliqué, chronologie impossible. Aucune " +
        "n'est une preuve, et aucune ne modifie la note : c'est vous qui " +
        "tranchez, en laissant une trace.",
    },
    {
      cible: '[data-visite="nav:/assistant"]',
      titre: "L'assistant",
      texte:
        "Posez vos questions en langage courant : « quels sont les meilleurs " +
        "profils ? », « qu'est-ce qui attend une décision ? ». Les chiffres " +
        "sont calculés en base et les sources sont citées.",
    },
    {
      cible: '[data-visite="notifications"]',
      titre: "Vos notifications",
      texte:
        "Nouvelle candidature, profil au score élevé, anomalie relevée : les " +
        "événements qui appellent votre attention remontent ici.",
    },
    ETAPE_PROFIL,
  ],

  admin: [
    {
      cible: null,
      titre: "Bienvenue sur SkillSeek AI",
      texte:
        "Voici les écrans de gouvernance de la plateforme. Vous pouvez " +
        "interrompre à tout moment et reprendre depuis votre profil.",
    },
    {
      cible: '[data-visite="nav:/admin/recruteurs"]',
      titre: "Les demandes de comptes",
      texte:
        "Un recruteur ne peut pas se connecter avant votre validation. Chaque " +
        "demande est accompagnée d'indices — nature du domaine, comptes déjà " +
        "validés, ressemblance avec un domaine connu — qui éclairent la " +
        "décision sans la remplacer.",
    },
    {
      cible: '[data-visite="nav:/admin/roles"]',
      titre: "Rôles et permissions",
      texte:
        "Les droits sont relus en base à chaque requête : retirer une " +
        "permission prend effet immédiatement, sans attendre l'expiration des " +
        "sessions ouvertes.",
    },
    {
      cible: '[data-visite="nav:/signalements"]',
      titre: "Le contrôle des dossiers",
      texte:
        "Les anomalies relevées sur les candidatures remontent ici. Elles " +
        "appellent une décision humaine, et le motif du refus comme celui de " +
        "la confirmation sont conservés.",
    },
    {
      cible: '[data-visite="nav:/admin/journal"]',
      titre: "Le journal d'audit",
      texte:
        "Qui a fait quoi, quand, sur quel objet. Les entrées sont immuables et " +
        "survivent à la suppression de l'objet visé : c'est souvent après une " +
        "suppression qu'on a besoin de savoir qui l'a ordonnée.",
    },
    {
      cible: '[data-visite="nav:/admin/corbeille"]',
      titre: "La corbeille",
      texte:
        "Supprimer un compte ou une offre est réversible : l'élément part en " +
        "corbeille et reste restaurable. La suppression définitive se fait en " +
        "deux temps, délibérément.",
    },
    {
      cible: '[data-visite="nav:/assistant"]',
      titre: "L'assistant",
      texte:
        "Interrogez la plateforme en langage courant : comptes en attente, " +
        "signalements ouverts, activité récente. Il ne restitue pas le contenu " +
        "des candidatures — votre rôle ne détient pas ce droit.",
    },
    ETAPE_PROFIL,
  ],
};

/** Clé de mémorisation, propre à l'utilisateur et à la version du contenu. */
export const cleVisite = (utilisateur) =>
  `skillseek:visite:${utilisateur?.id ?? "anon"}:v${VERSION}`;
