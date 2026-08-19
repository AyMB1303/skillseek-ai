"""Formulation de la réponse à partir des documents retrouvés.

Trois fournisseurs sont pris en charge, essayés dans cet ordre :

  1. `ollama` — modèle de langue exécuté localement. Aucune donnée ne quitte
     la machine, aucune clé n'est nécessaire. C'est le mode recommandé
     lorsqu'on souhaite des réponses rédigées librement.
  2. `api`    — service distant compatible avec l'interface OpenAI
     (Groq, Together, etc.), activé uniquement si une clé est configurée.
  3. `gabarits` — synthèse déterministe à partir du contexte. Toujours
     disponible, sans dépendance ni modèle.

Le choix est automatique : le premier fournisseur opérationnel est retenu.
L'assistant reste donc fonctionnel quelle que soit la configuration.
"""
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

DELAI = 45  # secondes : un modele local sur processeur peut etre lent

# Duree pendant laquelle la disponibilite du modele local est tenue pour
# acquise. Sans ce cache, chaque question payait un aller-retour reseau — et
# lorsque le modele est arrete, le delai d'attente complet, plusieurs fois.
DUREE_SONDAGE = 60          # secondes
DELAI_SONDAGE = 1.5         # secondes : un service local repond en quelques ms

# Le modele reste charge en memoire entre deux questions. Sans cela, Ollama le
# decharge au bout de cinq minutes et la question suivante paie plusieurs
# secondes de rechargement depuis le disque — le symptome le plus visible de
# lenteur pour un utilisateur qui revient sur l'assistant.
MAINTIEN = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

# Le contexte transmis est borne : sur processeur, la lecture de l'invite
# represente l'essentiel du temps de reponse, et un document tronque a mille
# caracteres porte deja ce qui sert a repondre.
DOCUMENTS_TRANSMIS = 4
LONGUEUR_DOCUMENT = 1000

CONSIGNE = """Tu es l'assistant de SkillSeek AI, une plateforme de recrutement.
Tu accompagnes un recruteur ou un administrateur dans son travail quotidien.

Ce que tu sais du fonctionnement de la plateforme :
- Chaque CV déposé est lu automatiquement, y compris s'il est scanné, puis
  transformé en profil structuré : expériences datées, diplômes, langues,
  certifications, compétences.
- Ce profil est confronté à l'offre et reçoit une note sur 100 : compétences
  obligatoires 35, compétences souhaitées 10, proximité de sens avec l'offre
  25, expérience 20, diplôme 10.
- Une compétence obligatoire absente est éliminatoire. Un écart mesuré
  d'expérience ou de diplôme n'élimine pas : il devient une réserve affichée,
  et le diplôme peut être compensé par l'expérience.
- Une note inférieure à 50 écarte la candidature, qui reste consultable et
  repêchable. Parmi celles au-dessus, les dix meilleures forment la
  présélection.
- Un modèle d'apprentissage ajuste la note de plus ou moins 8 points au
  maximum ; il ne peut jamais rattraper une candidature écartée par une règle.

Règles de conduite :
- Tous les CHIFFRES doivent provenir des FAITS VÉRIFIÉS fournis. N'en invente
  aucun, ne fais aucun calcul qui ne s'y trouve pas déjà, ne cite aucun nom de
  candidat absent du contexte. Si un chiffre manque, dis-le simplement.
- En revanche, tu peux converser normalement : saluer, expliquer le
  fonctionnement de la plateforme, reformuler, conseiller sur la manière de
  mener un recrutement, répondre à une question générale sur le métier.
- Réponds en français, sur un ton professionnel et direct. Deux à six phrases
  en général, davantage si la question appelle une explication.
- Ne mentionne jamais que tu disposes d'un « contexte » ou de « documents ».
- La note est une aide à la décision : le choix final appartient au recruteur.
  Rappelle-le quand c'est pertinent, sans le répéter à chaque réponse."""


CONSIGNE_ADMINISTRATION = """Tu es l'assistant de SkillSeek AI, une plateforme de
recrutement. Tu accompagnes un ADMINISTRATEUR de la plateforme, dont le travail
porte sur la gouvernance et non sur le recrutement lui-même.

Ce que tu sais du fonctionnement de la plateforme :
- Un compte recruteur n'est pas actif à l'inscription : un administrateur doit
  valider la demande, car publier une offre engage l'entreprise représentée.
  Chaque demande est accompagnée d'indices — nature du domaine de l'adresse,
  comptes déjà validés sur ce domaine, ressemblance avec un domaine connu.
  Ces indices ne bloquent rien : une messagerie grand public est fréquente chez
  les très petites entreprises et n'est pas un motif de refus.
- Les permissions sont relues en base à chaque requête sensible : retirer un
  droit prend effet immédiatement, sans attendre l'expiration des sessions.
  Le rôle administrateur ne bénéficie d'aucun contournement.
- Des contrôles automatiques relèvent des anomalies sur les candidatures. Un
  signalement n'est jamais une preuve, ne modifie ni la note ni le statut, et
  attend une décision humaine.
- Le journal d'audit est immuable et survit à la suppression des objets visés.
- La suppression des comptes et des offres est logique : l'élément part en
  corbeille et reste restaurable.

Règles de conduite :
- Tous les CHIFFRES doivent provenir des FAITS VÉRIFIÉS fournis. N'en invente
  aucun et ne fais aucun calcul qui ne s'y trouve pas déjà.
- Tu ne restitues PAS le contenu des dossiers de candidature : le rôle
  administrateur ne détient pas ce droit. Si la question porte sur des
  candidats, dis que cela relève de l'espace du recruteur.
- Réponds en français, sur un ton professionnel et direct. Deux à six phrases
  en général, davantage si la question appelle une explication.
- Ne mentionne jamais que tu disposes d'un « contexte » ou de « documents »."""


# --------------------------------------------------------------------------
# Modèle local (Ollama)
# --------------------------------------------------------------------------

SCHEMAS_AUTORISES = ("http", "https")


def _url_ollama():
    """Adresse du modèle local, dont le schéma est vérifié à la source.

    `urlopen` accepte `file://`, et une adresse mal formée — ou modifiée par
    quelqu'un ayant la main sur l'environnement — transformerait un appel
    réseau en lecture de fichier local. Le contrôle est posé ici, au point
    unique où la valeur entre dans le programme, plutôt que répété devant
    chaque appel.
    """
    url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
    if urllib.parse.urlparse(url).scheme not in SCHEMAS_AUTORISES:
        raise ValueError(
            f"OLLAMA_URL doit employer un schéma parmi {SCHEMAS_AUTORISES}."
        )
    return url


def _modele_ollama():
    return os.getenv("OLLAMA_MODEL", "qwen2.5:3b")


_sondage = {"instant": 0.0, "disponible": False}


def ollama_disponible(force=False):
    """Indique si un modèle local répond, sans resonder à chaque question.

    Le résultat est retenu une minute. C'est un compromis assumé : démarrer
    Ollama pendant une conversation ne sera pris en compte qu'au sondage
    suivant, mais l'assistant cesse de payer un aller-retour réseau — et,
    quand le service est arrêté, un délai d'attente complet — à chaque
    question posée.
    """
    maintenant = time.monotonic()
    if not force and maintenant - _sondage["instant"] < DUREE_SONDAGE:
        return _sondage["disponible"]

    try:
        requete = urllib.request.Request(f"{_url_ollama()}/api/tags")
        with urllib.request.urlopen(  # nosec B310 - schema verifie par _url_ollama
            requete, timeout=DELAI_SONDAGE
        ) as reponse:
            modeles = json.loads(reponse.read()).get("models", [])
            disponible = len(modeles) > 0
    except Exception:
        disponible = False

    _sondage.update(instant=maintenant, disponible=disponible)
    return disponible


def _echanges(historique, limite=4):
    """Reprend les derniers tours de parole, pour que le fil se tienne.

    Le rappel est court volontairement. Une reprise implicite — « et les
    autres ? » — porte sur le tour precedent, rarement au-dela ; transmettre
    six longs echanges rallongeait l'invite sans rien apporter, alors que le
    temps de lecture de l'invite domine sur processeur.
    """
    if not historique:
        return []
    return [
        {
            "role": "assistant" if (m.get("role") == "assistant") else "user",
            "content": (m.get("texte") or "")[:500],
        }
        for m in historique[-limite:]
        if (m.get("texte") or "").strip()
    ]


def _transcription(historique):
    lignes = [
        f"{'Assistant' if m['role'] == 'assistant' else 'Utilisateur'} : {m['content']}"
        for m in _echanges(historique)
    ]
    return "CONVERSATION EN COURS :\n" + "\n".join(lignes) + "\n\n" if lignes else ""


def _generer_ollama(question, contexte, historique=None, consigne=CONSIGNE):
    invite = (
        f"{consigne}\n\nCONTEXTE :\n{contexte}\n\n"
        f"{_transcription(historique)}"
        f"QUESTION : {question}\n\nRÉPONSE :"
    )
    corps = json.dumps({
        "model": _modele_ollama(),
        "prompt": invite,
        "stream": False,
        "keep_alive": MAINTIEN,
        # Une temperature un peu plus haute rend la formulation moins
        # mecanique ; les chiffres restant imposes par le contexte, elle ne
        # met pas l'exactitude en peril.
        #
        # `num_predict` borne la longueur produite. Chaque mot genere coute du
        # temps sur processeur : la consigne demande deux a six phrases, en
        # autoriser trois cents jetons suffit et evite les reponses qui
        # s'etirent sans rien ajouter.
        "options": {
            "temperature": 0.4,
            "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "300")),
        },
    }).encode("utf-8")

    requete = urllib.request.Request(
        f"{_url_ollama()}/api/generate",
        data=corps,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(  # nosec B310 - schema verifie par _url_ollama
        requete, timeout=DELAI
    ) as reponse:
        return json.loads(reponse.read()).get("response", "").strip()


# --------------------------------------------------------------------------
# Service distant compatible OpenAI
# --------------------------------------------------------------------------

def _cle_api():
    return os.getenv("LLM_API_KEY")


def api_disponible():
    return bool(_cle_api())


def _generer_api(question, contexte, historique=None, consigne=CONSIGNE):
    base = os.getenv("LLM_API_URL", "https://api.groq.com/openai/v1")
    modele = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

    messages = [{"role": "system", "content": f"{consigne}\n\nCONTEXTE :\n{contexte}"}]
    messages += _echanges(historique)
    messages.append({"role": "user", "content": question})

    corps = json.dumps({
        "model": modele,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 500,
    }).encode("utf-8")

    requete = urllib.request.Request(
        f"{base}/chat/completions",
        data=corps,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_cle_api()}",
        },
    )
    with urllib.request.urlopen(  # nosec B310 - schema verifie par _url_ollama
        requete, timeout=DELAI
    ) as reponse:
        donnees = json.loads(reponse.read())
        return donnees["choices"][0]["message"]["content"].strip()


# --------------------------------------------------------------------------
# Synthèse par gabarits
# --------------------------------------------------------------------------

def _generer_gabarits(question, documents, faits=None, redacteur=None):
    """Rédige la réponse à partir de l'intention reconnue et des faits calculés.

    Ce mode ne reformule pas librement : il compose. L'exactitude est garantie
    — aucun chiffre n'est produit ailleurs que par une requête en base — et le
    comportement reste reproductible d'un appel à l'autre.

    `redacteur` permet au domaine administration d'apporter ses propres
    intentions : ses questions ne recouvrent pas celles du recrutement.
    """
    from . import redaction

    composer = redacteur or redaction.composer

    if faits is None:
        # Sans faits chiffres, seules les fiches d'aide restent exploitables.
        fiches = [d for d in documents if d.type == "aide"]
        if fiches:
            return fiches[0].texte.strip()
        return (
            "Je n'ai pas trouvé d'information permettant de répondre à cette "
            "question. Reformulez-la ou consultez directement l'écran concerné."
        )

    return composer(question, documents, faits)


# --------------------------------------------------------------------------
# Point d'entrée
# --------------------------------------------------------------------------

def fournisseur_actif():
    """Nom du fournisseur qui sera employé pour la prochaine génération."""
    if ollama_disponible():
        return "ollama"
    if api_disponible():
        return "api"
    return "gabarits"


def generer(question, documents, contexte_donnees="", faits=None, historique=None,
            consigne=CONSIGNE, redacteur=None):
    """Produit la réponse et indique le fournisseur employé.

    En cas d'échec d'un fournisseur (modèle arrêté, réseau indisponible),
    la rédaction déterministe prend le relais : l'utilisateur obtient
    toujours une réponse.
    """
    contexte = contexte_donnees + "\n\n" if contexte_donnees else ""
    contexte += "\n\n".join(
        f"[{d.titre}]\n{d.texte[:LONGUEUR_DOCUMENT]}"
        for d in documents[:DOCUMENTS_TRANSMIS]
    )

    fournisseur = fournisseur_actif()

    if fournisseur == "ollama":
        try:
            reponse = _generer_ollama(question, contexte, historique, consigne)
            if reponse:
                return reponse, "ollama"
        except Exception as exc:
            logger.warning("Génération locale indisponible (%s) : repli.", exc)

    elif fournisseur == "api":
        try:
            reponse = _generer_api(question, contexte, historique, consigne)
            if reponse:
                return reponse, "api"
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            logger.warning("Service de génération indisponible (%s) : repli.", exc)

    return _generer_gabarits(question, documents, faits, redacteur), "gabarits"
