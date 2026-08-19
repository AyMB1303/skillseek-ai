"""Rédaction déterministe des réponses de l'assistant.

Ce module est le **mode de fonctionnement par défaut** de l'assistant, celui
qui s'applique lorsqu'aucun modèle de langue n'est disponible. Sa conception
répond à une contrainte précise du projet : ne dépendre d'aucun service payant
ni d'aucune clé d'interface, tout en restant utilisable.

Le principe est celui d'un **agent conversationnel à intentions** : la question
est ramenée à une intention connue, puis la réponse est composée à partir des
grandeurs calculées en base. Il en découle deux propriétés que n'offre aucun
modèle génératif :

  * **aucun chiffre ne peut être inventé** — les nombres proviennent tous de
    requêtes, jamais d'une reformulation ;
  * **la même question produit toujours la même réponse**, ce qui rend le
    comportement vérifiable et reproductible.

La limite est assumée : l'assistant ne traite que les intentions prévues.
Hors de celles-ci, il le dit et propose ce qu'il sait faire, plutôt que de
produire une réponse approximative. Lorsqu'un modèle de langue est configuré,
c'est lui qui rédige, et ce module lui sert de filet.
"""
import random
import re
import unicodedata

from ..scoring import PLAFOND_TOP, SEUIL_RETENU


def _normaliser(texte):
    """Minuscules sans accents : « écartée » et « ecartee » se rejoignent."""
    nfkd = unicodedata.normalize("NFKD", (texte or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# --------------------------------------------------------------------------
# Reconnaissance de l'intention
# --------------------------------------------------------------------------
#
# L'ordre compte : les intentions les plus specifiques sont testees en
# premier. « Combien de candidatures sont ecartees » doit etre reconnu comme
# une question sur les ecartees, non comme une demande de volumes.

INTENTIONS = [
    # --- Échanges de civilité et méta-questions ---
    ("salutation", r"^\s*(bonjour|bonsoir|salut|coucou|hello|hey|hi|yo|salam|slm)\b"),
    ("remerciement", r"\b(merci|thanks|thank you|nickel|parfait|super)\b"),
    ("adieu", r"\b(au revoir|bye|a bientot|bonne journee|bonne soiree|salut a toi)\b"),
    ("politesse", r"\b(ca va|comment vas[- ]tu|comment allez[- ]vous|tu vas bien)\b"),
    ("identite", r"(qui es[- ]tu|tu es qui|c'est quoi ton nom|presente[- ]toi|es[- ]tu (une |un )?(ia|robot|humain))"),  # noqa: E501
    ("capacites", r"(que (sais|peux)[- ]tu|tes capacites|a quoi sers[- ]tu|comment (tu |ca )?(marche|fonctionne)|que puis[- ]je (te )?demander|aide[- ]moi|besoin d'aide|^\s*aide\s*$)"),  # noqa: E501

    # --- Questions portant sur les données ---
    ("top_profils", r"(meilleur|top ?\d*|classement|shortlist|presele|plus haut|premiers profils)"),
    ("en_attente", r"(en attente|attendent? une decision|a traiter|a decider|sans decision|a valider|que dois[- ]je faire|mes taches|urgent)"),  # noqa: E501
    ("ecartees", r"(ecart|rejet|refus|non retenu|elimine|disqualifi|sous le seuil)"),
    ("entonnoir", r"(entonnoir|funnel|conversion|pipeline|taux de)"),
    ("par_offre", r"(par offre|chaque offre|comparer les offres|mes offres|offre la plus)"),
    ("sans_note", r"(sans note|non analyse|pas de score|illisible|echec de lecture)"),
    ("volumes", r"(combien|nombre de|volume|statistique|chiffres|resume|bilan|situation|etat des lieux)"),  # noqa: E501
    ("moyenne", r"(moyenne|score moyen|note moyenne)"),

    # --- Questions portant sur le fonctionnement ---
    ("explication_score", r"(comment.*(score|note)|calcul (du|de la)|pondera|composante|bareme)"),
    ("explication_seuil", r"(seuil|pourquoi 50|regle rg|top 10|comment.*retenu)"),
    ("explication_reserve", r"(reserve|sous reserve|equivalen|tolerance)"),
    ("explication_modele", r"(modele|apprentissage|intelligence artificielle|\bia\b|machine learning|entraine)"),  # noqa: E501
    ("explication_ats", r"(ats|analyse du cv|extraction|parsing|ocr|lecture du cv|profil extrait)"),
    ("explication_biais", r"(biais|discrimination|equite|genre|age|origine)"),
]


def intention(question):
    q = _normaliser(question)
    for nom, motif in INTENTIONS:
        if re.search(motif, q):
            return nom
    return "inconnue"


SOCIALES = {"salutation", "remerciement", "adieu", "politesse", "identite", "capacites"}


# --------------------------------------------------------------------------
# Formulations
# --------------------------------------------------------------------------

def _accord(nombre, singulier, pluriel=None):
    return singulier if nombre <= 1 else (pluriel or singulier + "s")


def _phrase_volumes(f):
    if not f["candidatures_total"]:
        return "Aucune candidature n'a encore été reçue."

    phrase = (
        f"Vous avez reçu {f['candidatures_total']} "
        f"{_accord(f['candidatures_total'], 'candidature')} sur "
        f"{f['offres_total']} {_accord(f['offres_total'], 'offre')}"
    )
    if f["offres_ouvertes"] != f["offres_total"]:
        phrase += f", dont {f['offres_ouvertes']} encore ouvertes"
    phrase += "."

    if f["candidatures_analysees"]:
        phrase += (
            f" {f['candidatures_analysees']} ont été analysées, "
            f"{f['au_dessus_du_seuil']} atteignent le seuil de {SEUIL_RETENU} points"
        )
        if f["note_moyenne"] is not None:
            phrase += f", et la note moyenne s'établit à {f['note_moyenne']} sur 100"
        phrase += "."
    return phrase


def _phrase_attente(f):
    if not f["en_attente_de_decision"]:
        return "Aucune candidature n'attend de décision de votre part."
    return (
        f"{f['en_attente_de_decision']} "
        f"{_accord(f['en_attente_de_decision'], 'candidature')} "
        f"{_accord(f['en_attente_de_decision'], 'attend', 'attendent')} "
        f"une décision. Le tableau ci-dessous les classe par note décroissante."
    )


SALUTATIONS = [
    "Bonjour. Que souhaitez-vous savoir sur vos recrutements ?",
    "Bonjour. Je peux vous renseigner sur vos offres, vos candidatures et le calcul des notes.",
    "Bonjour. Posez-moi une question sur vos candidatures en cours.",
]


def _reponse_sociale(nom, f):
    """Répond aux échanges de civilité, en ramenant vers l'usage utile."""
    if nom == "salutation":
        base = random.choice(SALUTATIONS)  # nosec B311
        if f["en_attente_de_decision"]:
            base += (
                f" À noter : {f['en_attente_de_decision']} "
                f"{_accord(f['en_attente_de_decision'], 'candidature')} "
                f"{_accord(f['en_attente_de_decision'], 'attend', 'attendent')} "
                f"une décision."
            )
        return base

    if nom == "remerciement":
        return "Avec plaisir. N'hésitez pas si vous avez d'autres questions."

    if nom == "adieu":
        return "Bonne continuation. Je reste disponible pour vos prochaines questions."

    if nom == "politesse":
        return (
            "Tout va bien, merci. Je suis prêt à vous renseigner sur l'état de "
            "vos recrutements."
        )

    if nom == "identite":
        return (
            "Je suis l'assistant de SkillSeek AI. Je réponds à vos questions en "
            "consultant directement les données de la plateforme : offres, "
            "candidatures, notes et règles de présélection. Les chiffres que je "
            "donne sont calculés en base, jamais estimés."
        )

    if nom == "capacites":
        return (
            "Je peux vous renseigner sur quatre choses.\n\n"
            "L'état de vos recrutements : volumes, candidatures en attente, "
            "taux de conversion de l'entonnoir.\n"
            "Le classement des candidats : meilleurs profils, candidatures "
            "écartées et leurs motifs, comparaison entre vos offres.\n"
            "Le fonctionnement du calcul : composition de la note, seuil de "
            "présélection, critères éliminatoires et réserves.\n"
            "L'analyse des CV : ce que le système extrait d'un document et "
            "comment il le confronte à l'offre.\n\n"
            "Posez votre question en langage courant."
        )
    return None


# --------------------------------------------------------------------------
# Composition de la réponse
# --------------------------------------------------------------------------

def _depuis_documents(documents, limite=2):
    """Reprend le contenu des fiches d'aide, rédigées pour être lues telles quelles."""
    fiches = [d for d in documents if d.type == "aide"]
    if fiches:
        return "\n\n".join(d.texte.strip() for d in fiches[:limite])
    return None


def composer(question, documents, f):
    """Produit la réponse correspondant à l'intention reconnue."""
    nom = intention(question)

    if nom in SOCIALES:
        return _reponse_sociale(nom, f)

    # Les questions de fonctionnement sont documentees : les fiches d'aide
    # sont redigees pour etre restituees sans reformulation.
    if nom.startswith("explication_"):
        texte = _depuis_documents(documents)
        if texte:
            return texte

    if nom == "top_profils":
        if not f["au_dessus_du_seuil"]:
            return (
                f"Aucune candidature n'atteint pour l'instant le seuil de "
                f"{SEUIL_RETENU} points. Les profils les plus proches restent "
                f"consultables dans l'onglet « Écartées », classés par note."
            )
        nombre = min(f["au_dessus_du_seuil"], PLAFOND_TOP)
        return (
            f"{f['au_dessus_du_seuil']} "
            f"{_accord(f['au_dessus_du_seuil'], 'candidature')} "
            f"{_accord(f['au_dessus_du_seuil'], 'dépasse', 'dépassent')} le seuil "
            f"de {SEUIL_RETENU} points. Voici les {nombre} "
            f"{_accord(nombre, 'meilleure')} par note décroissante. "
            f"La note synthétise les compétences, l'expérience, le diplôme et la "
            f"proximité avec l'offre : la décision d'entretien vous appartient."
        )

    if nom == "en_attente":
        return _phrase_attente(f)

    if nom == "ecartees":
        ecartees = f["candidatures_analysees"] - f["au_dessus_du_seuil"]
        if not ecartees:
            return "Aucune candidature analysée n'a été écartée."
        return (
            f"{ecartees} {_accord(ecartees, 'candidature')} "
            f"{_accord(ecartees, 'a', 'ont')} été "
            f"{_accord(ecartees, 'écartée')}, faute d'atteindre le seuil de "
            f"{SEUIL_RETENU} points. Chacune conserve le motif exact de son "
            f"écartement, et sa note reflète l'ampleur de l'écart : les plus "
            f"proches du seuil sont les premières à repêcher. Aucune n'est "
            f"supprimée."
        )

    if nom == "entonnoir":
        if not f["candidatures_total"]:
            return "Aucune candidature n'a encore été reçue : l'entonnoir est vide."
        return (
            f"Sur {f['candidatures_total']} "
            f"{_accord(f['candidatures_total'], 'candidature')} "
            f"{_accord(f['candidatures_total'], 'reçue')}, "
            f"{f['au_dessus_du_seuil']} "
            f"{_accord(f['au_dessus_du_seuil'], 'franchit', 'franchissent')} le "
            f"seuil, {f['entretiens']} "
            f"{_accord(f['entretiens'], 'est', 'sont')} en entretien et "
            f"{f['recrutes']} "
            f"{_accord(f['recrutes'], 'a', 'ont')} été "
            f"{_accord(f['recrutes'], 'recruté')}. Le détail étape par étape "
            f"figure ci-dessous."
        )

    if nom == "par_offre":
        if not f["offres_total"]:
            return "Vous n'avez encore publié aucune offre."
        return (
            f"Voici vos {f['offres_total']} "
            f"{_accord(f['offres_total'], 'offre')}, avec le nombre de "
            f"candidatures reçues, la note moyenne obtenue et le nombre "
            f"d'entretiens engagés."
        )

    if nom == "sans_note":
        if not f["candidatures_sans_note"]:
            return (
                "Toutes les candidatures reçues ont pu être analysées : aucun "
                "document n'a résisté à la lecture."
            )
        return (
            f"{f['candidatures_sans_note']} "
            f"{_accord(f['candidatures_sans_note'], 'candidature')} "
            f"{_accord(f['candidatures_sans_note'], 'n a', 'n ont')} pas pu être "
            f"analysée : le document n'a pas livré de texte exploitable. Elles "
            f"figurent dans l'onglet « Sans score », distinctement des "
            f"candidatures écartées — l'absence de note ne présume pas de la "
            f"qualité du profil. Vous pouvez relancer l'analyse ou saisir le "
            f"profil manuellement."
        ).replace("n a", "n'a").replace("n ont", "n'ont")

    if nom == "moyenne":
        if f["note_moyenne"] is None:
            return "Aucune candidature n'a encore reçu de note."
        return (
            f"La note moyenne s'établit à {f['note_moyenne']} sur 100, avec un "
            f"maximum de {f['note_maximale']} et un minimum de "
            f"{f['note_minimale']}. Le tableau par offre, ci-dessous s'il est "
            f"joint, permet de voir quelles offres attirent les profils les "
            f"plus adaptés."
        )

    if nom == "volumes":
        return _phrase_volumes(f)

    # --- Intention non reconnue ---
    texte = _depuis_documents(documents, limite=1)
    if texte:
        return texte

    return (
        "Je n'ai pas su rattacher votre question à ce que je sais faire.\n\n"
        "Je peux vous renseigner sur l'état de vos recrutements, le classement "
        "des candidats, les motifs d'écartement et le fonctionnement du calcul "
        "des notes. Essayez par exemple : « quels sont les meilleurs profils ? », "
        "« combien de candidatures attendent une décision ? » ou « comment la "
        "note est-elle calculée ? »."
    )


# --------------------------------------------------------------------------
# Relances proposées à l'utilisateur
# --------------------------------------------------------------------------

RELANCES = {
    "salutation": ["Quels sont les meilleurs profils ?",
                   "Combien de candidatures attendent une décision ?",
                   "Comment la note est-elle calculée ?"],
    "capacites": ["Fais-moi un bilan de la situation",
                  "Quelles candidatures ont été écartées et pourquoi ?",
                  "Quel est le score moyen par offre ?"],
    "identite": ["Comment la note est-elle calculée ?",
                 "Le modèle d'apprentissage intervient-il dans la note ?"],
    "top_profils": ["Quelles candidatures attendent une décision ?",
                    "Pourquoi certaines candidatures sont-elles écartées ?"],
    "en_attente": ["Quels sont les meilleurs profils ?",
                   "Montre-moi l'entonnoir de conversion"],
    "ecartees": ["Comment la note est-elle calculée ?",
                 "Qu'est-ce qu'une candidature retenue sous réserve ?"],
    "entonnoir": ["Quel est le score moyen par offre ?",
                  "Quelles candidatures attendent une décision ?"],
    "volumes": ["Quels sont les meilleurs profils ?",
                "Montre-moi l'entonnoir de conversion"],
    "explication_score": ["Qu'est-ce qu'une candidature retenue sous réserve ?",
                          "Le modèle d'apprentissage intervient-il dans la note ?"],
    "inconnue": ["Fais-moi un bilan de la situation",
                 "Quels sont les meilleurs profils ?",
                 "Comment la note est-elle calculée ?"],
}


def relances(question):
    """Questions de suivi proposées, adaptées à ce qui vient d'être demandé."""
    return RELANCES.get(intention(question), RELANCES["inconnue"])
