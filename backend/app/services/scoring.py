"""Moteur de score hybride : règles métiers, proximité sémantique, modèle appris.

Le calcul suit les conventions des systèmes de suivi des candidatures :

  * les compétences se répartissent entre exigences **obligatoires** — dont
    l'absence disqualifie — et compétences **souhaitées**, qui valorisent le
    profil sans être bloquantes ;
  * l'expérience et le diplôme annoncés sont traités comme des repères et non
    comme des couperets : un écart mesuré produit une **réserve** affichée, un
    écart important seul disqualifie ;
  * tout écartement conserve son motif exact, condition de l'explicabilité, et
    la note d'une candidature écartée reste ordonnée selon l'ampleur de
    l'écart, de sorte qu'un repêchage puisse être priorisé ;
  * le score final reste sur 100, quelles que soient les composantes
    disponibles, afin que les candidatures demeurent comparables.

Le modèle d'apprentissage supervisé n'entre pas dans la pondération : il
applique un **ajustement borné** au score établi par les règles. Ce choix
tient à la mesure de ses performances — le modèle apporte un gain réel mais
modeste, insuffisant pour lui confier une part fixe du score. Il départage
donc des profils que les règles jugent équivalents, sans jamais pouvoir
rattraper une candidature écartée pour un motif explicite.

Règle RG-01 : score < 50 -> écartée (conservée, repêchable) ;
parmi les >= 50, les 10 meilleures forment la shortlist.
"""
from .competences import canoniser


SEUIL_RETENU = 50
PLAFOND_TOP = 10

# Ponderation des composantes du score (total = 100)
POIDS_COMPETENCES = 35   # competences obligatoires
POIDS_SOUHAITEES = 10    # competences appreciees
POIDS_SEMANTIQUE = 25
POIDS_EXPERIENCE = 20
POIDS_DIPLOME = 10

# Amplitude maximale de l'ajustement apporte par le modele appris, en points
AMPLITUDE_MODELE = 8

# Part accordee a une competence obligatoire citee dans le curriculum mais que
# le recit d'experience ne rattache a aucune pratique.
#
# Le principe d'abord. Une competence citee ne vaut ni sa valeur pleine —
# rien ne la demontre — ni zero : sur le jeu de validation, les profils
# pleinement adaptes n'etayent eux-memes que 73 % des competences qu'ils
# possedent, contre 33 % pour les negatifs difficiles. Un curriculum n'est pas
# un inventaire exhaustif, et penaliser a fond punirait la sobriete d'un
# candidat plutot que son incompetence.
#
# La valeur, ensuite, vient du balayage de « mesurer_credit.py » et non d'un
# jugement. Le critere de choix etait fixe avant d'en lire le resultat : ne
# retenir qu'un palier couvrant plusieurs valeurs mesurees, jamais un maximum
# isole — avec huit negatifs difficiles, une seule decision qui bascule
# deplace la precision de deux points et demi, et un pic vaudrait du bruit.
#
#   credit   precision   rappel      F1
#   ------------------------------------
#     1,00      78,9 %   93,8 %   0,857
#     0,80      83,3 %   93,8 %   0,882
#     0,70      85,7 %   93,8 %   0,896   <- palier
#     0,60      85,7 %   93,8 %   0,896   <- palier
#     0,50      85,3 %   90,6 %   0,879
#     0,00      89,3 %   78,1 %   0,833
#
# Le palier 0,60–0,70 domine toutes les autres valeurs sur les trois
# indicateurs a la fois, et il est le seul a satisfaire les deux cibles du
# cahier des charges. 0,65 en est le centre : le point le plus eloigne des
# deux bornes ou le comportement change.
#
# Reserve de methode, qui doit rester dite : ce reglage est choisi sur le jeu
# qui sert ensuite a le mesurer. Le chiffre obtenu est donc une borne haute,
# non une estimation de terrain.
CREDIT_DECLAREE = 0.65

# En deca de cette part de competences etayees, une reserve est posee. Elle
# n'ecarte pas : elle nomme, dans le detail du calcul, ce que le recruteur doit
# verifier lui-meme.
SEUIL_ETAYAGE = 0.5

# Deux echelles, parce que deux questions distinctes se posaient sous une
# seule table.
#
# ANNEES_DIPLOME dit combien d'annees d'etudes un diplome represente. C'est
# l'information qu'on affiche, et celle qui sert a comparer deux candidats.
#
# RANGS_DIPLOME dit de combien de *diplomes* deux niveaux sont separes. C'est
# la seule qui doive entrer dans une regle, et elle n'a rien a voir avec la
# premiere : une licence et un master sont deux diplomes adjacents, meme si
# deux annees les separent.
#
# Confondre les deux avait une consequence qu'aucun test ne montrait : l'ecart
# entre Bac+3 et Bac+5 valait 2, franchissait le seuil de la reserve et rendait
# la candidature eliminatoire. La branche « un niveau d'ecart » etait donc
# inatteignable pour le cas le plus frequent qu'elle etait censee traiter.
ANNEES_DIPLOME = {"bac": 0, "bac+2": 2, "bac+3": 3, "bac+5": 5, "doctorat": 8}
NIVEAUX_DIPLOME = {"bac": 0, "bac+2": 1, "bac+3": 2, "bac+5": 3, "doctorat": 4}

# --------------------------------------------------------------------------
# Qualification : ce qui élimine, ce qui n'est qu'une réserve
# --------------------------------------------------------------------------
#
# Les systemes professionnels de suivi des candidatures distinguent deux
# natures d'exigences, et cette distinction est reprise ici :
#
#   * les **compétences indispensables** sont de vrais critères bloquants.
#     Un poste exigeant la fiscalité ne peut être tenu sans elle.
#
#   * l'**expérience** et le **diplôme** annoncés sont, dans la pratique du
#     recrutement, des reperes plutot que des seuils. Les annonces ecrivent
#     « 5 ans » en visant un profil confirme, et « Bac+5 ou experience
#     equivalente ». Un recruteur recoit couramment un candidat a quatre ans
#     sur un poste affiche a cinq. Les traiter comme des couperets ecarterait
#     des profils que l'entreprise aurait voulu voir.
#
# Un ecart mesure sur ces deux criteres produit donc une **réserve** : la
# candidature reste eligible, la reserve est affichee, et le point perdu se
# reflete dans la note. Au-dela d'une marge, l'ecart redevient eliminatoire.

# Part minimale de l'experience requise en deca de laquelle l'ecart n'est plus
# une reserve mais une disqualification.
#
# L'intention ecrite ici etait « quatre ans sur six ». Elle n'etait pas
# implementee : a 0,7, quatre ans sur six donne 0,667, passe sous le seuil, et
# devient eliminatoire — l'exemple meme que le commentaire donnait comme
# tolerable etait rejete par la constante qu'il documentait. Meme cas pour
# deux ans sur trois.
#
# Deux tiers implemente ce que la regle annonce : un manque d'un tiers de
# l'experience demandee reste une reserve, au-dela il disqualifie. Ce choix est
# coherent avec le principe pose plus haut — l'experience annoncee est un
# repere, pas un couperet — et avec la pratique des annonces, qui ecrivent
# « 3 ans » en recevant des candidats a deux.
TOLERANCE_EXPERIENCE = 2 / 3

# Chaque niveau de diplome manquant est compense par cette avance
# d'experience. Transposition de la clause « ou experience equivalente », que
# les annonces expriment sous la forme « Master, ou Licence avec cinq ans ».
EXPERIENCE_EQUIVALENTE = 2

# Penalites appliquees aux candidatures ecartees, afin que la note conserve
# un ordre : un profil auquel il manque une competence doit rester au-dessus
# de celui auquel il en manque trois.
PLAFOND_ECARTEE = 45
PENALITE_COMPETENCE = 4
PENALITE_ANNEE = 3
PENALITE_NIVEAU = 5


def exigences_canoniques(libelles):
    """Ramene les competences d'une offre a la forme du referentiel.

    Le referentiel etait applique au curriculum et pas a l'offre. Les deux
    cotes de la comparaison ne parlaient donc pas la meme langue : le CV
    produisait « javascript », et une offre redigee « JS » — ou « K8s »,
    « Postgres », « React.js », « Spring Boot » — ne trouvait jamais preneur.
    La competence etait declaree absente, ce qui est un critere eliminatoire :
    un recruteur ecrivant l'abreviation usuelle de son metier ecartait tous
    ses candidats, sans qu'aucun message ne le signale.

    Le libelle d'origine est conserve : c'est celui que le recruteur a ecrit,
    et c'est donc celui qu'il doit relire dans la liste des competences
    manquantes.

    Retourne [(forme_canonique, libelle_affiche)].
    """
    paires = []
    for libelle in libelles or []:
        canonique = canoniser(libelle) or (libelle or "").lower()
        paires.append((canonique.lower(), libelle))
    return paires


def _niveau(libelle, defaut=-1):
    return NIVEAUX_DIPLOME.get((libelle or "").lower(), defaut)


def qualifier(profil, offre):
    """Confronte le profil aux exigences et classe chaque écart.

    Retourne (eliminatoires, reserves, mesures) où `mesures` porte les écarts
    chiffrés, réutilisés pour la pénalité et pour l'explication affichée.
    """
    exigences = exigences_canoniques(offre.required_skills)
    possedees = {s.lower() for s in profil.get("skills", [])}
    # Le libelle du recruteur est affiche, la forme canonique compare.
    manquantes = [affiche for cle, affiche in exigences if cle not in possedees]

    experience = profil.get("experience_years", 0) or 0
    requise = offre.min_experience_years or 0
    diplome = profil.get("degree")
    diplome_requis = getattr(offre, "min_degree", None)

    eliminatoires, reserves = [], []
    mesures = {
        "competences_manquantes": len(manquantes),
        "annees_manquantes": max(0, requise - experience),
        "niveaux_manquants": 0,
        "diplome_conforme": True,
        "diplome_par_equivalence": False,
    }

    # --- Competences indispensables : seul veritable critere bloquant ---
    if manquantes:
        eliminatoires.append(
            "Compétence(s) obligatoire(s) absente(s) : " + ", ".join(manquantes)
        )

    # --- Experience : reserve dans la marge, disqualification au-dela ---
    if requise and experience < requise:
        if experience < requise * TOLERANCE_EXPERIENCE:
            eliminatoires.append(
                f"Expérience {experience} an(s), très en deçà des "
                f"{requise} an(s) attendus"
            )
        else:
            reserves.append(
                f"Expérience {experience} an(s) pour {requise} attendus — "
                f"écart d'un an ou deux, jugé rattrapable"
                if requise - experience <= 2
                else f"Expérience {experience} an(s) pour {requise} attendus"
            )

    # --- Diplome : equivalence par l'experience, puis reserve, puis rejet ---
    if diplome_requis:
        ecart = _niveau(diplome_requis, 0) - _niveau(diplome)
        if ecart > 0:
            mesures["niveaux_manquants"] = ecart
            # Deux annees d'experience au-dela du requis par niveau manquant
            besoin = requise + EXPERIENCE_EQUIVALENTE * ecart
            if experience >= besoin:
                mesures["diplome_par_equivalence"] = True
                reserves.append(
                    f"Diplôme {diplome or 'non renseigné'} pour {diplome_requis} "
                    f"attendu, compensé par {experience} ans d'expérience"
                )
            elif ecart <= 1:
                mesures["diplome_conforme"] = False
                reserves.append(
                    f"Diplôme {diplome or 'non renseigné'} pour {diplome_requis} "
                    f"attendu — un niveau d'écart"
                )
            else:
                mesures["diplome_conforme"] = False
                eliminatoires.append(
                    f"Diplôme {diplome or 'non renseigné'} très en deçà de "
                    f"{diplome_requis} requis"
                )

    return eliminatoires, reserves, mesures


def _penalite(mesures):
    """Écarte les candidatures disqualifiées sans les rendre indistinctes."""
    return (
        mesures["competences_manquantes"] * PENALITE_COMPETENCE
        + mesures["annees_manquantes"] * PENALITE_ANNEE
        + mesures["niveaux_manquants"] * PENALITE_NIVEAU
    )


def calculer_score(profil, offre, similarite_semantique=None, probabilite_modele=None):
    """Compare un profil extrait du CV à une offre.

    profil : dict {skills: [str], experience_years: int, degree: str}
    similarite_semantique : proximité [0, 1] entre le texte du CV et celui de
        l'offre, ou None lorsqu'elle n'a pas pu être calculée (saisie manuelle
        du profil, ou texte du CV indisponible).
    probabilite_modele : probabilité [0, 1] que le profil convienne, issue du
        modèle appris, ou None lorsqu'aucun modèle n'est disponible.

    Retourne (score, details) — details sert a l'explicabilite cote interface.
    """
    exigences = exigences_canoniques(offre.required_skills)
    exigences_souhaitees = exigences_canoniques(
        getattr(offre, "preferred_skills", None)
    )
    possedees = {s.lower() for s in profil.get("skills", [])}
    requises = [cle for cle, _ in exigences]
    souhaitees = [cle for cle, _ in exigences_souhaitees]

    # « trouvees » porte la forme canonique : c'est elle qui sert ensuite a
    # verifier l'etayage, lui aussi canonique. « manquantes » porte le libelle
    # du recruteur, qui doit s'y reconnaitre.
    trouvees = [cle for cle, _ in exigences if cle in possedees]
    manquantes = [affiche for cle, affiche in exigences if cle not in possedees]
    bonus_trouvees = [cle for cle, _ in exigences_souhaitees if cle in possedees]

    # Preuve : la competence apparait-elle dans le recit de l'experience, ou
    # seulement dans la liste declarative du curriculum ?
    #
    # Quand l'information n'a pas pu etre etablie — profil saisi a la main,
    # aucune experience datee reconnue — toutes les competences trouvees sont
    # tenues pour etayees. Le doute ne se paie pas.
    etayees_brutes = profil.get("skills_etayees")
    if etayees_brutes is None:
        etayees = set(trouvees)
    else:
        etayees = {s.lower() for s in etayees_brutes}
    competences_etayees = [s for s in trouvees if s in etayees]
    competences_declarees = [s for s in trouvees if s not in etayees]

    experience = profil.get("experience_years", 0) or 0

    # 1. Qualification : chaque ecart est classe, avec son motif exact.
    eliminatoires, reserves, mesures = qualifier(profil, offre)

    if trouvees and etayees_brutes is not None:
        part_etayee = len(competences_etayees) / len(trouvees)
        if part_etayee < SEUIL_ETAYAGE:
            reserves.append(
                "Compétence(s) obligatoire(s) citée(s) sans apparaître dans "
                "l'expérience décrite : " + ", ".join(competences_declarees)
            )

    # 2. Composantes du score
    #
    #    Le poids d'une composante indisponible est redistribue sur les
    #    competences obligatoires, afin que le total reste sur 100 et que les
    #    candidatures demeurent comparables entre elles.
    poids_competences = POIDS_COMPETENCES
    if similarite_semantique is None:
        poids_competences += POIDS_SEMANTIQUE
    if not souhaitees:
        poids_competences += POIDS_SOUHAITEES

    # Une competence etayee compte pleinement ; une competence seulement
    # declaree compte pour moitie. Ni un ni zero : elle n'est ni demontree ni
    # dementie, et la traiter comme absente reviendrait a exiger du candidat
    # qu'il raconte tout ce qu'il sait faire.
    credit = (
        len(competences_etayees) + CREDIT_DECLAREE * len(competences_declarees)
    )
    part_competences = (
        (credit / len(requises) * poids_competences) if requises else poids_competences
    )
    part_souhaitees = (
        (len(bonus_trouvees) / len(souhaitees) * POIDS_SOUHAITEES) if souhaitees else 0.0
    )
    part_semantique = (
        (similarite_semantique or 0.0) * POIDS_SEMANTIQUE
        if similarite_semantique is not None
        else 0.0
    )
    # Deux lectures de l'experience, et elles ne servent pas au meme endroit.
    #
    # L'anciennete brute repond a « le candidat a-t-il la seniorite annoncee ».
    # C'est elle qui qualifie ou disqualifie, parce que c'est elle que l'offre
    # demande explicitement.
    #
    # L'experience *pertinente* repond a « combien de ce temps touche aux
    # competences du poste ». Elle pondere chaque poste occupe par la part des
    # competences exigees que sa description fait apparaitre : huit ans passes
    # a autre chose ne valent pas huit ans sur le sujet.
    #
    # Seule la seconde entre dans la note. La faire entrer aussi dans la
    # disqualification a ete mesure : le rappel tombait a 65 %, parce qu'un
    # curriculum sobre est alors traite comme un curriculum sans experience.
    # Ecarter quelqu'un sur ce qu'il n'a pas ecrit serait exactement
    # l'injustice silencieuse que ce projet combat ; le signaler dans la note,
    # que le recruteur lit avec son detail, ne l'est pas.
    pertinente = profil.get("experience_pertinente")
    if pertinente is None:
        pertinente = experience
    if offre.min_experience_years:
        ratio = min(pertinente / offre.min_experience_years, 1.5) / 1.5
    else:
        ratio = 1.0
    part_experience = ratio * POIDS_EXPERIENCE

    # Le diplome rapporte tout s'il est conforme, y compris par equivalence ;
    # la moitie lorsqu'il manque un niveau non compense ; rien au-dela.
    if mesures["diplome_conforme"]:
        part_diplome = float(POIDS_DIPLOME)
    elif mesures["niveaux_manquants"] <= 1:
        part_diplome = POIDS_DIPLOME / 2
    else:
        part_diplome = 0.0

    score_regles = (
        part_competences + part_souhaitees + part_semantique + part_experience + part_diplome
    )

    # 3. Ajustement du modele appris.
    #
    #    Une probabilite de 0,5 laisse le score inchange ; elle le deplace au
    #    plus de AMPLITUDE_MODELE points dans un sens ou dans l'autre. Le
    #    modele n'intervient pas sur une candidature deja ecartee par une
    #    regle : la decision est alors prise sur un motif explicite, et aucun
    #    avis statistique ne doit pouvoir la renverser.
    ajustement = 0.0
    if probabilite_modele is not None and not eliminatoires:
        ajustement = (probabilite_modele - 0.5) * 2 * AMPLITUDE_MODELE

    score = round(score_regles + ajustement)
    if eliminatoires:
        # La candidature passe sous le seuil, mais sa note continue de refleter
        # l'ampleur de l'ecart : une competence manquante ne se confond pas avec
        # trois, et le recruteur peut trier ses ecartees pour un repechage.
        score = min(score, PLAFOND_ECARTEE - _penalite(mesures))
    score = max(0, min(100, score))

    composantes = [
        {
            "libelle": "Compétences obligatoires",
            "valeur": round(part_competences),
            "max": round(poids_competences),
        },
    ]
    if souhaitees:
        composantes.append(
            {
                "libelle": "Compétences souhaitées",
                "valeur": round(part_souhaitees),
                "max": POIDS_SOUHAITEES,
            }
        )
    if similarite_semantique is not None:
        composantes.append(
            {
                "libelle": "Proximité sémantique CV / offre",
                "valeur": round(part_semantique),
                "max": POIDS_SEMANTIQUE,
            }
        )
    composantes += [
        {
            "libelle": "Années d'expérience",
            "valeur": round(part_experience),
            "max": POIDS_EXPERIENCE,
        },
        {"libelle": "Niveau de diplôme", "valeur": part_diplome, "max": POIDS_DIPLOME},
    ]

    details = {
        "competences_trouvees": trouvees,
        "competences_manquantes": manquantes,
        # Publiees pour que le detail du calcul puisse dire « citee, non
        # etayee » plutot qu'un ecart de points inexplique.
        "competences_etayees": competences_etayees,
        "competences_declarees": competences_declarees,
        # Publie pour que l'interface enonce la part reellement appliquee au
        # lieu de la recopier : une constante recopiee finit par diverger.
        "credit_declaree": CREDIT_DECLAREE,
        "competences_souhaitees_trouvees": bonus_trouvees,
        "competences_souhaitees_manquantes": [
            affiche for cle, affiche in exigences_souhaitees if cle not in possedees
        ],
        "eliminatoires": eliminatoires,
        "reserves": reserves,
        "composantes": composantes,
        "version_moteur": "ats-4.0",
    }

    if probabilite_modele is not None:
        details["modele"] = {
            "probabilite": round(probabilite_modele, 3),
            "ajustement": round(ajustement, 1),
            "score_avant_ajustement": round(score_regles),
            "amplitude_maximale": AMPLITUDE_MODELE,
            "applique": bool(ajustement) and not eliminatoires,
            "commentaire": (
                "Candidature écartée par une règle : l'avis du modèle n'est pas appliqué."
                if eliminatoires
                else None
            ),
        }

    return score, details


def appliquer_regle_top(candidatures):
    """Sépare les candidatures selon la règle RG-01."""
    retenues = [c for c in candidatures if (c.score or 0) >= SEUIL_RETENU]
    retenues.sort(key=lambda c: c.score or 0, reverse=True)
    return {
        "top": retenues[:PLAFOND_TOP],
        "ecartees": [c for c in candidatures if (c.score or 0) < SEUIL_RETENU],
    }
