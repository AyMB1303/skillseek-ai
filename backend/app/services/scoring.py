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

NIVEAUX_DIPLOME = {"bac": 0, "bac+2": 2, "bac+3": 3, "bac+5": 5, "doctorat": 8}

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

# Part minimale de l'experience requise en deca de laquelle l'ecart n'est
# plus une reserve mais une disqualification (70 % : quatre ans sur six).
TOLERANCE_EXPERIENCE = 0.7

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


def _niveau(libelle, defaut=-1):
    return NIVEAUX_DIPLOME.get((libelle or "").lower(), defaut)


def qualifier(profil, offre):
    """Confronte le profil aux exigences et classe chaque écart.

    Retourne (eliminatoires, reserves, mesures) où `mesures` porte les écarts
    chiffrés, réutilisés pour la pénalité et pour l'explication affichée.
    """
    requises = [s.lower() for s in (offre.required_skills or [])]
    possedees = [s.lower() for s in profil.get("skills", [])]
    manquantes = [s for s in requises if s not in possedees]

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
    requises = [s.lower() for s in (offre.required_skills or [])]
    souhaitees = [s.lower() for s in (getattr(offre, "preferred_skills", None) or [])]
    possedees = [s.lower() for s in profil.get("skills", [])]

    trouvees = [s for s in requises if s in possedees]
    manquantes = [s for s in requises if s not in possedees]
    bonus_trouvees = [s for s in souhaitees if s in possedees]

    experience = profil.get("experience_years", 0) or 0

    # 1. Qualification : chaque ecart est classe, avec son motif exact.
    eliminatoires, reserves, mesures = qualifier(profil, offre)

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

    part_competences = (
        (len(trouvees) / len(requises) * poids_competences) if requises else poids_competences
    )
    part_souhaitees = (
        (len(bonus_trouvees) / len(souhaitees) * POIDS_SOUHAITEES) if souhaitees else 0.0
    )
    part_semantique = (
        (similarite_semantique or 0.0) * POIDS_SEMANTIQUE
        if similarite_semantique is not None
        else 0.0
    )
    if offre.min_experience_years:
        ratio = min(experience / offre.min_experience_years, 1.5) / 1.5
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
        "competences_souhaitees_trouvees": bonus_trouvees,
        "competences_souhaitees_manquantes": [s for s in souhaitees if s not in possedees],
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
