#!/usr/bin/env python3
"""Fabrique les figures du rapport de stage.

Deux principes gouvernent ce fichier.

**Les figures se régénèrent.** Aucune n'est dessinée à la main dans un
éditeur : chacune sort d'une description textuelle versionnée à côté du code.
Si un modèle change, le diagramme de classes change avec lui à la commande
suivante. Une figure dessinée à la main, elle, devient fausse en silence.

**Elles doivent tenir en noir et blanc.** Le guide de l'ESI impose que les
figures restent lisibles sur une photocopie. L'information n'est donc jamais
portée par la couleur seule : elle l'est par la forme, le trait, le
remplissage et l'étiquette. La palette est volontairement réduite à quatre
niveaux de gris.

Usage :
    python docs/figures/generer.py            # toutes les figures
    python docs/figures/generer.py classes    # une seule

Dépendances : graphviz (commande « dot ») pour les schémas de structure,
ImageMagick (« convert ») pour rastériser les figures écrites en SVG.
"""
from __future__ import annotations

import os
import subprocess
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.abspath(os.path.join(ICI, "..", ".."))
DPI = "200"

# --- Palette -------------------------------------------------------------
#
# Le guide de l'ESI interdit la couleur **pour le texte** et exige que les
# figures restent lisibles **sur une photocopie**. Il n'interdit pas la
# couleur dans les figures : il impose qu'elles survivent au noir et blanc.
#
# Deux règles en découlent, et elles sont vérifiées par programme dans
# `verifier.py` :
#
#   1. Le texte noir posé sur un aplat clair conserve, une fois la figure
#      convertie en niveaux de gris, un contraste d'au moins 4,5 pour 1.
#      Les aplats retenus dépassent tous 15 pour 1.
#   2. Aucune information n'est portée par la teinte seule. Une catégorie se
#      reconnaît toujours aussi à sa forme, au style de son trait ou à son
#      étiquette — car en photocopie, les six aplats clairs deviennent six
#      gris voisins.
ENCRE       = "#12324F"   # texte et traits : bleu très sombre, pas du noir pur
PRIMAIRE    = "#1F4E79"   # bleu — présentation, structure
SECONDAIRE  = "#17706E"   # sarcelle — service applicatif
ACCENT      = "#9C6404"   # ambre — données et documents
SUCCES      = "#1F6B4A"   # vert — étapes validées, exploitation
ALERTE      = "#9B2F2F"   # brique — écartement, refus
NEUTRE      = "#5B6B7B"   # gris — éléments de contexte

BLANC       = "#FFFFFF"
BLEUCLAIR   = "#D7E5F2"
SARCCLAIR   = "#C9E4E2"
AMBRECLAIR  = "#F7E3B8"
VERTCLAIR   = "#CDE6D8"
BRIQUECLAIR = "#F3D6D2"
GRISCLAIR   = "#E8ECF0"

# Les trois noms hérités restent définis : plusieurs figures les emploient.
CLAIR = BLEUCLAIR
MOYEN = SARCCLAIR
FONCE = AMBRECLAIR

# Réglages communs à tous les graphes Graphviz.
ENTETE = f"""
  graph [fontname="Helvetica", fontsize=11, bgcolor="{BLANC}", pad=0.3,
         fontcolor="{ENCRE}"];
  node  [fontname="Helvetica", fontsize=11, color="{ENCRE}", penwidth=1.4,
         fontcolor="{ENCRE}"];
  edge  [fontname="Helvetica", fontsize=10, color="{NEUTRE}", penwidth=1.3,
         fontcolor="{ENCRE}"];
"""


def rendre_dot(nom: str, source: str) -> str:
    """Écrit la source .dot puis la rastérise."""
    chemin_dot = os.path.join(ICI, f"{nom}.dot")
    chemin_png = os.path.join(ICI, f"{nom}.png")
    with open(chemin_dot, "w", encoding="utf-8") as flux:
        flux.write(source)
    subprocess.run(
        ["dot", "-Tpng", f"-Gdpi={DPI}", chemin_dot, "-o", chemin_png], check=True
    )
    return chemin_png


def rendre_svg(nom: str, source: str) -> str:
    """Écrit la source SVG puis la rastérise."""
    chemin_svg = os.path.join(ICI, f"{nom}.svg")
    chemin_png = os.path.join(ICI, f"{nom}.png")
    with open(chemin_svg, "w", encoding="utf-8") as flux:
        flux.write(source)
    subprocess.run(
        ["convert", "-density", DPI, "-background", "white", "-flatten",
         chemin_svg, chemin_png],
        check=True,
    )
    return chemin_png


# ==========================================================================
# Lecture du modèle réel
# ==========================================================================

def metadonnees():
    """Renvoie les tables SQLAlchemy, lues depuis le code de l'application.

    Le diagramme de données n'est pas une transcription : c'est une
    projection du modèle exécuté. Il ne peut donc pas diverger du schéma
    réellement créé par les migrations.
    """
    sys.path.insert(0, os.path.join(RACINE, "backend"))
    os.environ.setdefault("FLASK_ENV", "testing")
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    from app import create_app  # noqa: E402
    from app.extensions import db  # noqa: E402

    application = create_app()
    with application.app_context():
        return {nom: db.metadata.tables[nom] for nom in sorted(db.metadata.tables)}


def _echapper(texte: str) -> str:
    for avant, apres in (("{", r"\{"), ("}", r"\}"), ("<", r"\<"), (">", r"\>"),
                         ("|", r"\|")):
        texte = texte.replace(avant, apres)
    return texte


def _type_court(colonne) -> str:
    """Type UML lisible, plutôt que le type SQL du dialecte courant."""
    brut = str(colonne.type).upper()
    for motif, propre in (
        ("VARCHAR", "String"), ("TEXT", "Text"), ("INTEGER", "int"),
        ("FLOAT", "float"), ("BOOLEAN", "bool"), ("DATETIME", "DateTime"),
        ("JSON", "JSON"),
    ):
        if brut.startswith(motif):
            return propre
    return brut.capitalize()


# ==========================================================================
# Figure 1 — Diagramme de classes du noyau métier
# ==========================================================================

# Le noyau seulement : six classes. Le modèle complet compte douze tables,
# mais les porter toutes sur une même page A4 rendrait les attributs
# illisibles. La figure suivante montre le schéma complet, en compact.
NOYAU = ["users", "roles", "permissions", "job_offers", "applications",
         "evaluations"]

NOMS_CLASSES = {
    "users": "Utilisateur", "roles": "Rôle", "permissions": "Permission",
    "job_offers": "Offre", "applications": "Candidature",
    "evaluations": "Évaluation", "signalements": "Signalement",
    "notifications": "Notification", "journal": "EntréeJournal",
    "ai_metrics": "MétriqueIA", "token_blocklist": "JetonRévoqué",
    "role_permissions": "role_permissions",
}

# Méthodes portées par les classes, relevées dans les modèles. Elles ne se
# déduisent pas du schéma : une table n'a pas de comportement, une classe si.
METHODES = {
    "users": ["+ set_password(mdp)", "+ check_password(mdp) : bool",
              "+ has_permission(code) : bool", "+ est_administrateur : bool",
              "+ est_verrouille : bool"],
    "job_offers": ["+ salaire_affiche : str", "+ is_deleted : bool"],
    "applications": ["+ is_deleted : bool"],
    "roles": ["+ to_dict() : dict"],
}


def _html(texte: str) -> str:
    return (texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("«", "&#171;").replace("»", "&#187;"))


def figure_classes(tables) -> str:
    # Étiquettes HTML plutôt que « record » : Graphviz refuse de tracer une
    # arête entre deux nœuds « record » placés sur un même rang, et perd
    # l'association sans autre avertissement qu'un message sur la sortie
    # d'erreur. Comme la mise en page en grille repose justement sur des
    # rangs partagés, trois associations disparaissaient de la figure.
    blocs = []
    for nom in NOYAU:
        table = tables[nom]
        lignes_attributs = []
        for colonne in table.columns:
            suffixe = ""
            if colonne.primary_key:
                suffixe = " &#171;PK&#187;"
            elif colonne.foreign_keys:
                suffixe = " &#171;FK&#187;"
            lignes_attributs.append(
                f"+ {_html(colonne.name)} : {_html(_type_court(colonne))}{suffixe}"
            )
        attributs = '<BR ALIGN="LEFT"/>'.join(lignes_attributs) + '<BR ALIGN="LEFT"/>'

        # Le compartiment des méthodes n'est émis que s'il y en a. Rendu
        # avec une chaîne vide, il produisait un rectangle coloré orphelin
        # sous « Permission » et « Évaluation » — deux classes qui ne portent
        # aucun comportement, ce qui est une information en soi, pas un trou.
        methodes = [_html(m) for m in METHODES.get(nom, [])]
        ligne_methodes = ""
        if methodes:
            corps = '<BR ALIGN="LEFT"/>'.join(methodes) + '<BR ALIGN="LEFT"/>'
            ligne_methodes = (
                f'<TR><TD ALIGN="LEFT" BALIGN="LEFT" BGCOLOR="{CLAIR}">'
                f'{corps}</TD></TR>'
            )

        titre = _html(NOMS_CLASSES[nom])
        blocs.append(
            f'  {nom} [shape=plaintext, label=<'
            f'<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6">'
            f'<TR><TD BGCOLOR="{MOYEN}"><B>{titre}</B></TD></TR>'
            f'<TR><TD ALIGN="LEFT" BALIGN="LEFT" BGCOLOR="{BLANC}">'
            f'{attributs}</TD></TR>'
            f'{ligne_methodes}'
            f'</TABLE>>];'
        )

    # Disposition en grille, imposée par « rank=same ».
    #
    # Laissée libre, la mise en page de Graphviz empile les six classes en
    # une colonne de 1340 sur 3514 pixels : un rapport de 0,38, impossible à
    # loger sur une page A4 sans réduire le texte au point de le rendre
    # illisible. En rangs forcés, la figure retrouve un format de page.
    grille = [
        "  { rank=same; roles; permissions; }",
        "  { rank=same; users; job_offers; }",
        "  { rank=same; applications; evaluations; }",
    ]

    # Associations : cardinalités aux deux extrémités et losange creux pour
    # l'agrégation, selon la notation UML. « constraint=false » sur les liens
    # internes à un rang : ils relient sans peser sur le calcul des rangs.
    liens = [
        '  roles -> users [dir=both, arrowtail=odiamond, arrowhead=none, '
        'taillabel="1", headlabel="0..*", labeldistance=2.2];',
        '  roles -> permissions [dir=both, arrowtail=none, arrowhead=none, '
        'constraint=false, taillabel="0..*", headlabel="0..*", '
        'labeldistance=2.2, label="attribue"];',
        '  users -> job_offers [dir=both, arrowtail=odiamond, arrowhead=none, '
        'constraint=false, taillabel="1", headlabel="0..*", '
        'labeldistance=2.2, label="publie"];',
        '  users -> applications [dir=both, arrowtail=odiamond, '
        'arrowhead=none, taillabel="1", headlabel="0..*", labeldistance=2.2, '
        'label="dépose"];',
        '  job_offers -> applications [dir=both, arrowtail=odiamond, '
        'arrowhead=none, taillabel="1", headlabel="0..*", labeldistance=2.2, '
        'label="reçoit"];',
        '  applications -> evaluations [dir=both, arrowtail=odiamond, '
        'arrowhead=none, constraint=false, taillabel="1", headlabel="0..1", '
        'labeldistance=2.2, label="est évaluée par"];',
    ]

    return (
        "digraph classes {\n" + ENTETE +
        "  rankdir=TB;\n  nodesep=1.0;\n  ranksep=0.9;\n"
        + "\n".join(blocs) + "\n" + "\n".join(grille) + "\n"
        + "\n".join(liens) + "\n}\n"
    )


# ==========================================================================
# Figure 2 — Schéma relationnel complet
# ==========================================================================

def figure_schema(tables) -> str:
    """Les douze tables : clés, puis décompte des colonnes ordinaires.

    Le diagramme de classes montre déjà tous les attributs du noyau. Répéter
    ici les seize colonnes de « users » gonflerait la figure sans rien
    apprendre : ce qu'on vient lire dans un schéma relationnel, ce sont les
    clés et les liens. Les colonnes ordinaires sont donc comptées, non
    listées — la figure reste lisible une fois imprimée.
    """
    blocs = []
    for nom, table in tables.items():
        cles, ordinaires = [], 0
        for colonne in table.columns:
            marques = []
            if colonne.primary_key:
                marques.append("PK")
            if colonne.foreign_keys:
                marques.append("FK")
            if colonne.unique and not colonne.primary_key:
                marques.append("U")
            if marques:
                cles.append(
                    f'<B>{",".join(marques)}</B> {_html(colonne.name)}'
                )
            else:
                ordinaires += 1
        if ordinaires:
            accord = "colonne" if ordinaires == 1 else "colonnes"
            cles.append(f"<I>+ {ordinaires} {accord}</I>")
        corps = '<BR ALIGN="LEFT"/>'.join(cles) + '<BR ALIGN="LEFT"/>'

        # La table d'association se distingue par le trait ET par le gris :
        # en photocopie, la nuance seule ne se lirait pas.
        assoc = nom == "role_permissions"
        blocs.append(
            f'  {nom} [shape=plaintext, label=<'
            f'<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5" '
            f'STYLE="ROUNDED">'
            f'<TR><TD BGCOLOR="{FONCE if assoc else MOYEN}">'
            f'<B>{_html(nom)}</B></TD></TR>'
            f'<TR><TD ALIGN="LEFT" BALIGN="LEFT" BGCOLOR="{BLANC}">'
            f'{corps}</TD></TR></TABLE>>];'
        )

    liens = []
    for nom, table in tables.items():
        for colonne in table.columns:
            for cle in colonne.foreign_keys:
                cible = cle.target_fullname.split(".")[0]
                liens.append(
                    f'  {nom} -> {cible} [arrowhead=none, arrowtail=crow, '
                    f'dir=back, fontsize=9, label="{colonne.name}"];'
                )

    return (
        "digraph schema {\n" + ENTETE +
        "  rankdir=TB;\n  nodesep=0.35;\n  ranksep=0.55;\n"
        + "\n".join(blocs) + "\n" + "\n".join(liens) + "\n}\n"
    )


# ==========================================================================
# Figure 3 — Diagramme de cas d'utilisation
# ==========================================================================

def figure_cas_utilisation() -> str:
    """Trois acteurs, une frontière de système, les cas par acteur.

    Écrit en SVG plutôt qu'en Graphviz : la notation UML demande des
    bonshommes-bâtons et une frontière de système rectangulaire, que
    Graphviz ne sait pas produire proprement.
    """
    L, H = 1215, 800

    def acteur(x, y, nom, role):
        return f'''
  <g stroke="#000" stroke-width="2" fill="none">
    <circle cx="{x}" cy="{y}" r="13"/>
    <line x1="{x}" y1="{y + 13}" x2="{x}" y2="{y + 48}"/>
    <line x1="{x - 20}" y1="{y + 26}" x2="{x + 20}" y2="{y + 26}"/>
    <line x1="{x}" y1="{y + 48}" x2="{x - 17}" y2="{y + 76}"/>
    <line x1="{x}" y1="{y + 48}" x2="{x + 17}" y2="{y + 76}"/>
  </g>
  <text x="{x}" y="{y + 96}" text-anchor="middle" font-family="Helvetica"
        font-size="15" font-weight="bold">{nom}</text>
  <text x="{x}" y="{y + 114}" text-anchor="middle" font-family="Helvetica"
        font-size="12">{role}</text>'''

    def cas(x, y, texte, gris=BLANC):
        lignes = texte.split("|")
        dy = -6 if len(lignes) > 1 else 5
        corps = "".join(
            f'<tspan x="{x}" dy="{0 if i == 0 else 15}">{ligne}</tspan>'
            for i, ligne in enumerate(lignes)
        )
        return f'''
  <ellipse cx="{x}" cy="{y}" rx="122" ry="28" fill="{gris}" stroke="#000"
           stroke-width="1.4"/>
  <text x="{x}" y="{y + dy}" text-anchor="middle" font-family="Helvetica"
        font-size="12.5">{corps}</text>'''

    def trait(x1, y1, x2, y2, pointille=False):
        style = ' stroke-dasharray="6,4"' if pointille else ""
        return (f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#000"'
                f' stroke-width="1.2"{style}/>')

    parties = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{L}" height="{H}" '
        f'viewBox="0 0 {L} {H}">',
        f'  <rect width="{L}" height="{H}" fill="{BLANC}"/>',
        # Frontière du système : tout ce que la plateforme réalise est dedans,
        # y compris l'analyse du CV, qui n'est pas un acteur extérieur.
        '  <rect x="282" y="28" width="706" height="742" fill="none" '
        'stroke="#000" stroke-width="1.8"/>',
        '  <text x="635" y="56" text-anchor="middle" font-family="Helvetica" '
        'font-size="15" font-weight="bold">SkillSeek AI</text>',
    ]

    parties.append(acteur(108, 150, "Candidat", "dépose et suit"))
    parties.append(acteur(108, 452, "Recruteur", "publie et décide"))
    parties.append(acteur(1098, 618, "Administrateur", "gouverne les accès"))

    cas_candidat = [
        (468, 112, "Consulter les offres"),
        (468, 180, "Déposer une candidature"),
        (468, 248, "Suivre l'état de ses|candidatures"),
        (468, 316, "Voir les compétences|manquantes"),
    ]
    cas_recruteur = [
        (468, 402, "Publier une offre"),
        (468, 470, "Consulter le classement|justifié"),
        (468, 538, "Repêcher une candidature|écartée"),
        (468, 606, "Évaluer après entretien"),
    ]
    cas_admin = [
        (806, 620, "Valider un compte|recruteur"),
        (806, 700, "Attribuer rôles|et permissions"),
    ]

    for x, y, t in cas_candidat:
        parties.append(cas(x, y, t))
    for x, y, t in cas_recruteur:
        parties.append(cas(x, y, t, CLAIR))
    for x, y, t in cas_admin:
        parties.append(cas(x, y, t, MOYEN))

    # Cas interne, déclenché par le dépôt et non par un acteur.
    parties.append(cas(806, 180, "Analyser le CV|et calculer la note", FONCE))
    parties.append(
        '  <text x="659" y="168" text-anchor="middle" font-family="Helvetica" '
        'font-size="11" font-style="italic">&#171;include&#187;</text>'
    )
    # Flèche ouverte, conforme à la notation d'une dépendance «include».
    parties.append(trait(592, 180, 700, 180, pointille=True))
    parties.append(
        '  <polyline points="690,174 702,180 690,186" fill="none" '
        'stroke="#000" stroke-width="1.4"/>'
    )

    for _, y, _ in cas_candidat:
        parties.append(trait(138, 208, 348, y))
    for _, y, _ in cas_recruteur:
        parties.append(trait(138, 510, 348, y))
    for _, y, _ in cas_admin:
        parties.append(trait(1068, 676, 942, y))

    # Légende : indispensable, puisque le gris ne se lit pas seul en photocopie.
    parties.append(f'''
  <rect x="20" y="640" width="248" height="122" fill="none" stroke="#000"
        stroke-width="1"/>
  <text x="32" y="662" font-family="Helvetica" font-size="12"
        font-weight="bold">Légende</text>
  <ellipse cx="48" cy="683" rx="18" ry="9" fill="{BLANC}" stroke="#000"/>
  <text x="76" y="687" font-family="Helvetica" font-size="11.5">cas du candidat</text>
  <ellipse cx="48" cy="706" rx="18" ry="9" fill="{CLAIR}" stroke="#000"/>
  <text x="76" y="710" font-family="Helvetica" font-size="11.5">cas du recruteur</text>
  <ellipse cx="48" cy="729" rx="18" ry="9" fill="{MOYEN}" stroke="#000"/>
  <text x="76" y="733" font-family="Helvetica" font-size="11.5">cas de l'administrateur</text>
  <ellipse cx="48" cy="752" rx="18" ry="9" fill="{FONCE}" stroke="#000"/>
  <text x="76" y="756" font-family="Helvetica" font-size="11.5">traitement interne</text>''')

    parties.append("</svg>")
    return "\n".join(parties)


# ==========================================================================
# Figure 4 — Diagramme de séquence : analyse d'une candidature
# ==========================================================================

def figure_sequence() -> str:
    """Le chemin complet, du dépôt du CV à la note justifiée."""
    L, H = 1120, 800
    participants = [
        (78, "Candidat", "acteur"),
        (250, "Interface", "Next.js"),
        (430, "API", "Flask"),
        (622, "Lecture ATS", "spaCy, OCR"),
        (810, "Notation", "scoring.py"),
        (1000, "Base", "PostgreSQL"),
    ]
    haut, bas = 96, 745

    # Les pointes de flèche sont dessinées en polygones plutôt qu'en
    # « marker » SVG : plusieurs rastériseurs, dont celui d'ImageMagick,
    # ignorent silencieusement les marqueurs. Un diagramme de séquence sans
    # flèches ne veut plus rien dire, et la perte serait passée inaperçue.
    parties = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{L}" height="{H}" '
        f'viewBox="0 0 {L} {H}">',
        f'  <rect width="{L}" height="{H}" fill="{BLANC}"/>',
    ]

    for x, nom, sous in participants:
        parties.append(f'''
  <rect x="{x - 72}" y="30" width="144" height="52" fill="{CLAIR}"
        stroke="#000" stroke-width="1.4"/>
  <text x="{x}" y="52" text-anchor="middle" font-family="Helvetica"
        font-size="13" font-weight="bold">{nom}</text>
  <text x="{x}" y="70" text-anchor="middle" font-family="Helvetica"
        font-size="11">{sous}</text>
  <line x1="{x}" y1="{haut}" x2="{x}" y2="{bas}" stroke="#000"
        stroke-width="1" stroke-dasharray="7,5"/>''')

    def pointe(x, y, vers_droite, pleine=True):
        """Pointe de flèche : triangle plein pour un appel, chevron pour un retour."""
        d = 12 if vers_droite else -12
        if pleine:
            return (f'  <polygon points="{x},{y} {x - d},{y - 4.5} '
                    f'{x - d},{y + 4.5}" fill="#000"/>')
        return (f'  <polyline points="{x - d},{y - 5} {x},{y} {x - d},{y + 5}" '
                f'fill="none" stroke="#000" stroke-width="1.4"/>')

    def message(y, xa, xb, texte, retour=False, note=None):
        tiret = ' stroke-dasharray="7,4"' if retour else ""
        milieu = (xa + xb) / 2
        bloc = (
            f'  <line x1="{xa}" y1="{y}" x2="{xb}" y2="{y}" stroke="#000" '
            f'stroke-width="1.3"{tiret}/>\n'
            + pointe(xb, y, xb > xa, pleine=not retour) + "\n"
            f'  <text x="{milieu}" y="{y - 9}" text-anchor="middle" '
            f'font-family="Helvetica" font-size="11.5">{texte}</text>'
        )
        if note:
            bloc += (
                f'\n  <text x="{milieu}" y="{y + 16}" text-anchor="middle" '
                f'font-family="Helvetica" font-size="10.5" '
                f'font-style="italic">{note}</text>'
            )
        return bloc

    def auto_message(x, y, texte):
        """Message réflexif : la boucle rectangulaire de la notation UML."""
        return (
            f'  <polyline points="{x + 6},{y} {x + 62},{y} {x + 62},{y + 30} '
            f'{x + 14},{y + 30}" fill="none" stroke="#000" stroke-width="1.3"/>\n'
            + pointe(x + 8, y + 30, False) + "\n"
            f'  <text x="{x + 72}" y="{y + 20}" font-family="Helvetica" '
            f'font-size="11">{texte}</text>'
        )

    def activation(x, y1, y2):
        return (f'  <rect x="{x - 6}" y="{y1}" width="12" height="{y2 - y1}" '
                f'fill="{MOYEN}" stroke="#000" stroke-width="1"/>')

    parties.append(activation(250, 122, 706))
    parties.append(activation(430, 152, 668))
    parties.append(activation(622, 238, 320))
    parties.append(activation(810, 404, 500))

    parties += [
        message(122, 84, 238, "1. dépose son CV (PDF)"),
        message(152, 256, 418, "2. POST /applications"),
        message(190, 436, 988, "3. enregistre le fichier et la candidature"),
        message(238, 436, 610, "4. extraire le profil"),
        auto_message(622, 262, "lecture, et OCR si le PDF est une image"),
        message(320, 610, 442, "5. profil structuré", retour=True,
                note="compétences, expérience, diplôme"),
        message(404, 436, 798, "6. calculer la note"),
        auto_message(810, 428, "calcul des cinq composantes"),
        message(500, 798, 442, "7. note et détail par composante", retour=True,
                note="35 / 10 / 25 / 20 / 10, puis ±8 au plus"),
        message(560, 436, 988, "8. écrit score et score_details"),
        message(614, 424, 262, "9. candidature analysée", retour=True),
        message(668, 436, 988, "10. notifie le recruteur"),
        message(706, 238, 90, "11. accusé de dépôt", retour=True,
                note="aucune note n'est communiquée au candidat"),
    ]

    # Note attachée à l'étape de notation, par un trait d'ancrage discontinu.
    # Elle est placée à droite du diagramme, dans l'espace libre : posée sur
    # le flux des messages, elle en masquait un.
    # La règle RG-01 a sa propre figure, et sa place dans la légende du
    # rapport. L'encadré qui la rappelait ici occupait près du tiers de la
    # largeur, ce qui écrasait le texte de toute la figure à l'impression.

    parties.append(
        '  <text x="20" y="784" font-family="Helvetica" font-size="11" '
        'font-style="italic">Trait plein et pointe pleine : appel. '
        'Trait discontinu et chevron : retour.</text>'
    )
    parties.append("</svg>")
    return "\n".join(parties)


# ==========================================================================
# Figure 5 — Diagramme d'activité : la règle de présélection RG-01
# ==========================================================================

def figure_activite() -> str:
    return "digraph activite {\n" + ENTETE + f"""
  rankdir=TB; nodesep=0.45; ranksep=0.5;
  debut  [shape=circle, width=0.28, style=filled, fillcolor="#000000",
          label=""];
  // Un seul nœud de fin. Deux nœuds terminaux sont licites en UML, mais ici
  // ils laissaient croire à une branche oubliée : les trois issues sont bien
  // trois fins du même traitement.
  fin    [shape=doublecircle, width=0.26, style=filled,
          fillcolor="#000000", label=""];

  lire   [shape=box, style="rounded,filled", fillcolor="{CLAIR}",
          label="Lire le CV et reconstituer\\nle profil structuré"];
  noter  [shape=box, style="rounded,filled", fillcolor="{CLAIR}",
          label="Calculer les cinq composantes\\n35 + 10 + 25 + 20 + 10"];
  ajust  [shape=box, style="rounded,filled", fillcolor="{CLAIR}",
          label="Appliquer l'ajustement du modèle\\nborné à ±8 points"];

  seuil  [shape=diamond, style=filled, fillcolor="{MOYEN}", height=1.1,
          width=2.4, label="note ≥ 50 ?"];
  rang   [shape=diamond, style=filled, fillcolor="{MOYEN}", height=1.1,
          width=2.4, label="dans les dix\\nmeilleures ?"];

  ecart  [shape=box, style="rounded,filled", fillcolor="{FONCE}",
          label="Écartée du classement\\nconservée et repêchable"];
  hors   [shape=box, style="rounded,filled", fillcolor="{FONCE}",
          label="Retenue hors présélection\\nconsultable à la demande"];
  presel [shape=box, style="rounded,filled,bold", fillcolor="{MOYEN}",
          label="Présélectionnée\\nprésentée au recruteur"];

  debut -> lire -> noter -> ajust -> seuil;
  seuil -> ecart  [label="  non  "];
  seuil -> rang   [label="  oui  "];
  rang  -> presel [label="  oui  "];
  rang  -> hors   [label="  non  "];
  ecart -> fin;
  hors  -> fin;
  presel -> fin;

  note [shape=note, style=filled, fillcolor="{BLANC}", fontsize=10,
        label="Aucune candidature n'est supprimée.\\nLe recruteur peut repêcher\\nune candidature écartée."];
  ecart -> note [style=dashed, arrowhead=none, constraint=false];
{{ rank=same; ecart; note; }}
}}
"""


# ==========================================================================
# Figure 6 — Architecture en composants
# ==========================================================================

def figure_composants() -> str:
    # Disposition verticale, et non horizontale : de gauche à droite, les
    # trois groupes s'alignaient sur 3 806 pixels de large, ce qui réduit le
    # texte à 3,6 points une fois la figure posée sur une largeur de page.
    return "digraph composants {\n" + ENTETE + f"""
  rankdir=TB; nodesep=0.35; ranksep=0.5;
  compound=true;

  navigateur [shape=box, style="filled,rounded", fillcolor="{BLANC}",
              label="Navigateur\\ndu poste client"];

  subgraph cluster_hote {{
    label="Hôte d'exécution (Docker Compose ou groupe de conteneurs)";
    fontsize=12; style=dashed; color="#000000"; bgcolor="{BLANC}";

    proxy [shape=box3d, style=filled, fillcolor="{MOYEN}",
           label="Proxy inverse\\nnginx\\n:80"];

    subgraph cluster_front {{
      label="Présentation"; fontsize=11; style=solid; bgcolor="{CLAIR}";
      front [shape=component, style=filled, fillcolor="{BLANC}",
             label="Interface\\nNext.js 14 · React 18\\n:3000"];
    }}

    subgraph cluster_back {{
      label="Service applicatif"; fontsize=11; style=solid; bgcolor="{CLAIR}";
      api  [shape=component, style=filled, fillcolor="{BLANC}",
            label="API REST\\nFlask · JWT\\n:5000"];
      ats  [shape=component, style=filled, fillcolor="{BLANC}",
            label="Lecture de CV\\nspaCy · Tesseract"];
      note [shape=component, style=filled, fillcolor="{BLANC}",
            label="Notation\\nrègles + modèle appris"];
      rag  [shape=component, style=filled, fillcolor="{BLANC}",
            label="Assistant\\nrecherche documentaire"];
    }}

    bd [shape=cylinder, style=filled, fillcolor="{MOYEN}",
        label="PostgreSQL 16", height=1.0];
    fic [shape=folder, style=filled, fillcolor="{MOYEN}",
         label="Fichiers\\nCV déposés"];
  }}

  ollama [shape=box, style="filled,dashed", fillcolor="{FONCE}",
          label="Ollama — facultatif\\nmodèle de langage local\\nà défaut, réponse\\ndéterministe"];

  navigateur -> proxy   [label="  HTTPS  "];
  proxy -> front        [label="  /  "];
  proxy -> api          [label="  /api  "];
  front -> api          [style=dashed, label="  appels REST  "];
  api -> ats            [arrowhead=vee];
  api -> note           [arrowhead=vee];
  api -> rag            [arrowhead=vee];
  api -> bd             [label="  SQLAlchemy  "];
  ats -> fic            [label="  lit  "];
  rag -> ollama         [style=dashed, label="  HTTP local  "];
}}
"""


# ==========================================================================
# Figure 7 — Diagramme de déploiement
# ==========================================================================

def figure_deploiement() -> str:
    return "digraph deploiement {\n" + ENTETE + f"""
  rankdir=TB; nodesep=0.55; ranksep=0.75; compound=true;

  subgraph cluster_dev {{
    label="Poste de développement"; fontsize=12; style=solid;
    bgcolor="{BLANC}";
    poste [shape=box3d, style=filled, fillcolor="{CLAIR}",
           label="«device» Poste\\ndocker compose up -d\\nquatre conteneurs locaux"];
  }}

  subgraph cluster_forge {{
    label="Forge — GitHub"; fontsize=12; style=solid; bgcolor="{BLANC}";
    depot   [shape=box3d, style=filled, fillcolor="{CLAIR}",
             label="«device» Exécuteur GitHub Actions\\nsept travaux d'intégration"];
    registre [shape=cylinder, style=filled, fillcolor="{MOYEN}",
              label="«artifact» GHCR\\nimages étiquetées\\npar empreinte et version",
              height=1.1];
  }}

  subgraph cluster_azure {{
    label="Azure — groupe de conteneurs (Container Instances)";
    fontsize=12; style=solid; bgcolor="{CLAIR}";

    c_proxy [shape=box, style=filled, fillcolor="{MOYEN}",
             label="«container» proxy\\nnginx · 0,5 vCPU / 1 Gio\\nseul port exposé : 80"];
    c_front [shape=box, style=filled, fillcolor="{BLANC}",
             label="«container» frontend\\nNext.js · 0,5 vCPU / 1,5 Gio"];
    c_api   [shape=box, style=filled, fillcolor="{BLANC}",
             label="«container» backend\\nFlask · 2 vCPU / 8 Gio"];
    c_bd    [shape=box, style=filled, fillcolor="{BLANC}",
             label="«container» db\\nPostgreSQL · 0,5 vCPU / 1,5 Gio"];

    // Les liaisons internes portent l'adresse de bouclage, et non un nom de
    // service : c'est le fait marquant de ce mode de déploiement, et sans ces
    // arêtes les quatre conteneurs semblaient sans rapport entre eux.
    // Les quatre conteneurs restent sur un même rang : sans cette contrainte,
    // les liaisons ci-dessous les empilent en colonne et la figure passe de
    // 1 263 à 2 217 pixels de haut, soit vingt-huit centimètres à l'échelle
    // d'une page.
    {{ rank=same; c_proxy; c_front; c_api; c_bd; }}
    // Les poids fixent l'ordre de gauche à droite. Sans eux, Graphviz range
    // le frontal à l'extrémité et la liaison vers le port 3000 décrit une
    // arche par-dessus tout le groupe, jusque sur son titre.
    c_proxy -> c_front [label=" :3000 ", fontsize=9, weight=20];
    c_proxy -> c_api   [label=" :5000 ", fontsize=9, weight=1];
    c_api   -> c_bd    [label=" :5432 ", fontsize=9, weight=20];
  }}

  poste -> depot [label="  git push  "];
  depot -> registre [label="  publie les images  "];
  registre -> c_proxy [lhead=cluster_azure,
                       label="  étiquette de version → déploiement  "];

  legende [shape=note, style=filled, fillcolor="{BLANC}", fontsize=10,
           label="Les quatre conteneurs partagent un même espace réseau.\\nIls se joignent par l'adresse de bouclage, non par leur\\nnom de service : c'est ce que change un groupe de\\nconteneurs par rapport à Docker Compose."];
  c_bd -> legende [style=invis];
}}
"""


# ==========================================================================
# Figure 8 — Chaîne d'intégration et de livraison
# ==========================================================================

def figure_cicd() -> str:
    """La chaîne, de la poussée jusqu'au service qui répond.

    Sans aucun sous-graphe « cluster », et c'est délibéré. Un cadre de
    groupe et une contrainte « rank=same » ne peuvent pas coexister :
    Graphviz honore le rang et laisse les nœuds sortir du cadre, si bien que
    le cadre intitulé « sept travaux » n'en contenait plus qu'un seul. Le
    regroupement passe donc par le remplissage et le style du trait, que la
    légende explicite — ce qui vaut mieux en photocopie de toute façon.
    """
    return "digraph cicd {\n" + ENTETE + f"""
  rankdir=TB; nodesep=0.22; ranksep=0.55;
  node [shape=box, style="filled,rounded", fillcolor="{CLAIR}"];

  push [shape=ellipse, style=filled, fillcolor="{MOYEN}",
        label="Poussée sur main ou étiquette v*"];

  t1 [label="Backend\\nflake8 · 194 tests"];
  t2 [label="Frontend\\nESLint · build"];
  t3 [label="Dépendances\\npip-audit\\nnpm audit"];
  t4 [label="Dépôt\\nTrivy"];
  t5 [label="Code\\nBandit · Semgrep"];

  t7 [label="Assemblage\\nla pile complète\\ndémarre"];
  t6 [label="Images\\nconstruction et publication\\nGHCR + inventaire logiciel",
      fillcolor="{MOYEN}"];

  q1 [style="filled,rounded,dashed", label="CodeQL\\nflux de données\\n+ hebdomadaire"];
  q2 [style="filled,rounded,dashed", label="SonarCloud\\ncouverture · duplication\\nfiabilité · sécurité"];

  dep [shape=box, style="filled,bold", fillcolor="{MOYEN}",
       label="Déploiement\\nattend l'image au registre, crée le groupe\\nde conteneurs, puis interroge /api/ready\\ndepuis l'extérieur"];
  ok  [shape=ellipse, style=filled, fillcolor="{FONCE}",
       label="Succès déclaré seulement\\nsi le service répond"];

  push -> t1; push -> t2; push -> t3; push -> t4; push -> t5;
  push -> q1 [style=dashed]; push -> q2 [style=dashed];
  t1 -> t6; t2 -> t6; t3 -> t6; t4 -> t6; t5 -> t6;
  t1 -> t7 [style=dotted]; t2 -> t7 [style=dotted];
  {{ rank=same; t6; t7; q1; q2; }}
  t6 -> dep [label="  étiquette v* seulement  "];
  dep -> ok;

  legende [shape=note, style=filled, fillcolor="{BLANC}", fontsize=10,
           label="Trait plein : les sept travaux d'intégration.\\nTrait discontinu : analyses menées à part, dont\\nl'indisponibilité ne bloque ni la construction\\nni la publication."];
  ok -> legende [style=invis];
}}
"""


# ==========================================================================
# Figure 9 — Organigramme de l'organisme d'accueil
# ==========================================================================

def figure_organigramme() -> str:
    """Structure de BC Skills Group, et rattachement du stagiaire.

    Reconstituée depuis le site institutionnel de l'entreprise (pages « À
    propos » et « Direction »), consulté le 30 août 2026. Un organigramme
    trouvé dans un rapport antérieur donnait une structure sensiblement
    différente : elle ne correspond plus à ce que l'entreprise publie
    aujourd'hui, ce qui n'a rien d'étonnant pour une société passée de huit
    consultants en 2009 à plus de trois cents.

    Seules deux personnes sont nommées : le fondateur, parce qu'il incarne la
    direction, et l'encadrant du stage, parce que le lecteur doit savoir sous
    quelle responsabilité le travail a été conduit. Nommer l'ensemble de
    l'encadrement alourdirait la figure sans rien apprendre.
    """
    return "digraph organigramme {\n" + ENTETE + f"""
  rankdir=TB; nodesep=0.34; ranksep=0.6; splines=ortho;
  node [shape=box, style="filled,rounded", fillcolor="{BLANC}", height=0.62,
        margin="0.20,0.10"];
  edge [arrowhead=none, color="{NEUTRE}"];

  dg [style="filled,rounded", fillcolor="{PRIMAIRE}", fontcolor="{BLANC}",
      penwidth=1.8, label=<<B>Direction générale</B><BR/>
      <FONT POINT-SIZE="10">Mohammed Jebbar, fondateur</FONT>>];
  daf [style="filled,rounded", fillcolor="{BLEUCLAIR}", color="{PRIMAIRE}",
       label=<<B>Direction financière</B><BR/>
       <FONT POINT-SIZE="10">cofondateur</FONT>>];

  // Encadrement supérieur : quatre pôles. Celui qui accueille le stage est
  // souligné par un trait plus épais et un aplat distinct — la teinte seule
  // ne suffirait pas en photocopie.
  bd     [fillcolor="{GRISCLAIR}", color="{NEUTRE}",
          label=<<B>Développement</B><BR/><B>commercial</B>>];
  public [fillcolor="{GRISCLAIR}", color="{NEUTRE}",
          label=<<B>Secteur public</B>>];
  techno [fillcolor="{GRISCLAIR}", color="{NEUTRE}",
          label=<<B>Technologie</B><BR/><B>et ingénierie</B>>];
  conseil [fillcolor="{SARCCLAIR}", color="{SECONDAIRE}", penwidth=2.4,
           label=<<B>Services de conseil</B><BR/>
           <FONT POINT-SIZE="10">agence de Rabat</FONT>>];

  // L'agence de Rabat.
  cp    [fillcolor="{BLANC}", color="{SECONDAIRE}",
         label=<Chef de projet<BR/>technique>];
  ctech [fillcolor="{SARCCLAIR}", color="{SECONDAIRE}", penwidth=2.0,
         label=<<B>Consultants techniques</B><BR/>
         <FONT POINT-SIZE="10">dont l'encadrant du stage :</FONT><BR/>
         <FONT POINT-SIZE="10"><B>Houssam Haraf</B></FONT>>];
  cfonc [fillcolor="{BLANC}", color="{SECONDAIRE}",
         label=<Consultants<BR/>fonctionnels>];
  adm   [fillcolor="{BLANC}", color="{SECONDAIRE}",
         label=<Opérations<BR/>administratives>];

  // Le stagiaire : trait discontinu, parce que la position est temporaire et
  // n'appartient pas à la structure permanente.
  stagiaire [style="filled,rounded,dashed", fillcolor="{AMBRECLAIR}",
             color="{ACCENT}", penwidth=2.0,
             label=<<B>Stagiaire — PFA</B><BR/>
             <FONT POINT-SIZE="10">SkillSeek AI</FONT>>];

  dg -> daf [style=dashed, constraint=false];
  dg -> bd; dg -> public; dg -> techno;
  dg -> conseil [penwidth=2.2, color="{SECONDAIRE}"];
  conseil -> cp; conseil -> ctech [penwidth=2.0, color="{SECONDAIRE}"];
  conseil -> cfonc; conseil -> adm;
  ctech -> stagiaire [style=dashed, penwidth=2.0, color="{ACCENT}"];

  {{ rank=same; dg; daf; }}
  {{ rank=same; bd; public; techno; conseil; }}
  {{ rank=same; cp; ctech; cfonc; adm; }}

  legende [shape=note, style=filled, fillcolor="{GRISCLAIR}", color="{NEUTRE}",
           fontsize=10, margin="0.18,0.12",
           label=<<B>Repères</B><BR ALIGN="LEFT"/>
           Siège : Safi &#183; Conseil : Rabat &#183; EMEA : Londres<BR ALIGN="LEFT"/>
           Fondée en 2009 &#183; 300+ consultants &#183; 500+ clients<BR ALIGN="LEFT"/>
           Trait discontinu : rattachement temporaire<BR ALIGN="LEFT"/>
           <FONT POINT-SIZE="9">Source : site institutionnel, consulté le 30 août 2026</FONT><BR ALIGN="LEFT"/>>];
  adm -> legende [style=invis];
}}
"""


# ==========================================================================
# Figure 10 — Chaîne de traçabilité : du commit au conteneur qui répond
# ==========================================================================

def figure_tracabilite() -> str:
    """Comment une empreinte de commit devient un service qui répond.

    C'est la propriété qui distingue une livraison industrialisée d'un
    déploiement manuel : à tout instant, on peut désigner le commit exact
    qui tourne en production, et refaire le chemin dans les deux sens. Rien
    n'est reconstruit à l'étape suivante — c'est le même artefact qui
    progresse, ce qui rend la chaîne vérifiable.
    """
    L, H = 1400, 620
    etapes = [
        ("1", "Commit", "4d7328a", "empreinte SHA-1\ndu contenu du dépôt",
         PRIMAIRE, BLEUCLAIR),
        ("2", "Image", "ghcr.io/…:4d7328a", "construite une seule fois,\nétiquetée par l'empreinte",
         SECONDAIRE, SARCCLAIR),
        ("3", "Version", "v1.0.0", "la même image reçoit\nune étiquette lisible",
         ACCENT, AMBRECLAIR),
        ("4", "Exécution", "groupe de conteneurs", "l'artefact est tiré,\njamais reconstruit",
         SUCCES, VERTCLAIR),
    ]
    lx, ly, lw, lh = 60, 150, 290, 230
    ecart = 335

    parties = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{L}" height="{H}" '
        f'viewBox="0 0 {L} {H}">',
        f'  <rect width="{L}" height="{H}" fill="{BLANC}"/>',
        f'  <text x="60" y="62" font-family="Helvetica" font-size="20" '
        f'font-weight="bold" fill="{ENCRE}">Traçabilité : du commit au service '
        f'qui répond</text>',
        f'  <text x="60" y="92" font-family="Helvetica" font-size="13" '
        f'fill="{NEUTRE}">Le même artefact progresse d\'un bout à l\'autre. '
        f'Aucune étape ne reconstruit ce que la précédente a produit.</text>',
    ]

    for i, (num, titre, jeton, detail, trait, fond) in enumerate(etapes):
        x = lx + i * ecart
        parties.append(f'''
  <rect x="{x}" y="{ly}" width="{lw}" height="{lh}" rx="12" fill="{fond}"
        stroke="{trait}" stroke-width="3"/>
  <circle cx="{x + 34}" cy="{ly + 36}" r="19" fill="{trait}"/>
  <text x="{x + 34}" y="{ly + 42}" text-anchor="middle" font-family="Helvetica"
        font-size="16" font-weight="bold" fill="{BLANC}">{num}</text>
  <text x="{x + 66}" y="{ly + 43}" font-family="Helvetica" font-size="17"
        font-weight="bold" fill="{ENCRE}">{titre}</text>
  <rect x="{x + 20}" y="{ly + 74}" width="{lw - 40}" height="40" rx="6"
        fill="{BLANC}" stroke="{trait}" stroke-width="1.5"/>
  <text x="{x + lw / 2}" y="{ly + 100}" text-anchor="middle"
        font-family="monospace" font-size="15" fill="{ENCRE}">{jeton}</text>''')
        for j, ligne in enumerate(detail.split("\n")):
            parties.append(
                f'  <text x="{x + lw / 2}" y="{ly + 142 + j * 21}" '
                f'text-anchor="middle" font-family="Helvetica" font-size="12.5" '
                f'fill="{ENCRE}">{ligne}</text>'
            )
        if i < len(etapes) - 1:
            xa = x + lw
            xb = x + ecart
            parties.append(
                f'  <line x1="{xa + 4}" y1="{ly + lh / 2}" x2="{xb - 16}" '
                f'y2="{ly + lh / 2}" stroke="{NEUTRE}" stroke-width="3"/>'
                f'<polygon points="{xb - 4},{ly + lh / 2} {xb - 18},{ly + lh / 2 - 7} '
                f'{xb - 18},{ly + lh / 2 + 7}" fill="{NEUTRE}"/>'
            )

    # Le contrôle final : ce qui distingue « déployé » de « qui fonctionne ».
    parties.append(f'''
  <rect x="{lx}" y="428" width="1280" height="76" rx="12" fill="{BLANC}"
        stroke="{SUCCES}" stroke-width="3"/>
  <text x="{lx + 26}" y="458" font-family="Helvetica" font-size="15"
        font-weight="bold" fill="{ENCRE}">Contrôle de sortie</text>
  <text x="{lx + 26}" y="484" font-family="Helvetica" font-size="13"
        fill="{ENCRE}">La chaîne interroge <tspan font-family="monospace">/api/ready</tspan> depuis l'extérieur du réseau. L'exécution n'est déclarée réussie que si le service répond — non parce qu'une commande a rendu la main.</text>
  <text x="{lx}" y="548" font-family="Helvetica" font-size="12.5"
        fill="{NEUTRE}">Conséquence pratique : à tout instant, l'empreinte affichée par le registre désigne le commit exact qui tourne. Le chemin se refait dans les deux sens.</text>''')

    parties.append("</svg>")
    return "\n".join(parties)


# ==========================================================================
# Figure 10 bis — Chemin critique de la chaîne d'intégration
# ==========================================================================

def figure_temps_pipeline() -> str:
    """Durées réellement mesurées sur une exécution de la chaîne.

    Les valeurs proviennent de l'exécution nº 59 du 29 août 2026. L'intérêt
    n'est pas décoratif : la figure montre où passe le temps, et donc ce
    qu'il faudrait attaquer en premier pour raccourcir la boucle de retour.
    """
    L, H = 1340, 600
    x0, echelle = 430, 1.72   # 1,72 pixel par seconde
    travaux = [
        ("Backend — lint et 194 tests",        248, PRIMAIRE,   BLEUCLAIR, True),
        ("Démarrage de la pile complète",      156, SECONDAIRE, SARCCLAIR, False),
        ("Frontend — lint et construction",     50, PRIMAIRE,   BLEUCLAIR, False),
        ("Dépendances — vulnérabilités",        41, ACCENT,     AMBRECLAIR, False),
        ("Sécurité — analyse du code",          41, ALERTE,     BRIQUECLAIR, False),
        ("Sécurité — analyse du dépôt",         20, ALERTE,     BRIQUECLAIR, False),
    ]

    parties = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{L}" height="{H}" '
        f'viewBox="0 0 {L} {H}">',
        f'  <rect width="{L}" height="{H}" fill="{BLANC}"/>',
        f'  <text x="50" y="54" font-family="Helvetica" font-size="19" '
        f'font-weight="bold" fill="{ENCRE}">Où passe le temps dans la chaîne '
        f'd\'intégration</text>',
        f'  <text x="50" y="82" font-family="Helvetica" font-size="12.5" '
        f'fill="{NEUTRE}">Durées mesurées sur l\'exécution n&#186; 59 — les '
        f'travaux s\'exécutent en parallèle.</text>',
    ]

    for i, (nom, duree, trait, fond, critique) in enumerate(travaux):
        y = 116 + i * 52
        largeur = duree * echelle
        parties.append(f'''
  <text x="{x0 - 16}" y="{y + 22}" text-anchor="end" font-family="Helvetica"
        font-size="13" fill="{ENCRE}">{nom}</text>
  <rect x="{x0}" y="{y}" width="{largeur:.0f}" height="32" rx="5" fill="{fond}"
        stroke="{trait}" stroke-width="{3 if critique else 1.8}"/>
  <text x="{x0 + largeur + 12:.0f}" y="{y + 22}" font-family="Helvetica"
        font-size="12.5" font-weight="bold"
        fill="{ENCRE}">{duree // 60} min {duree % 60:02d} s</text>''')
        if critique:
            parties.append(
                f'  <text x="{x0 + 12}" y="{y + 21}" font-family="Helvetica" '
                f'font-size="12" font-weight="bold" fill="{ENCRE}">'
                f'chemin critique</text>'
            )

    parties.append(f'''
  <line x1="{x0}" y1="440" x2="{x0 + 248 * echelle:.0f}" y2="440"
        stroke="{ENCRE}" stroke-width="2.5"/>
  <text x="{x0}" y="466" font-family="Helvetica" font-size="12"
        fill="{ENCRE}">0</text>
  <text x="{x0 + 248 * echelle:.0f}" y="466" text-anchor="end"
        font-family="Helvetica" font-size="12" fill="{ENCRE}">4 min 08 s</text>
  <rect x="50" y="492" width="1240" height="72" rx="10" fill="{GRISCLAIR}"
        stroke="{NEUTRE}" stroke-width="1.5"/>
  <text x="70" y="520" font-family="Helvetica" font-size="13" font-weight="bold"
        fill="{ENCRE}">Ce que la mesure apprend</text>
  <text x="70" y="544" font-family="Helvetica" font-size="12.5" fill="{ENCRE}">Les tests du service applicatif portent à eux seuls le chemin critique : les cinq autres travaux se terminent avant eux.</text>
  <text x="70" y="562" font-family="Helvetica" font-size="12.5" fill="{ENCRE}">Raccourcir la boucle de retour passerait donc par la parallélisation des tests, non par l'optimisation des analyses de sûreté.</text>''')

    parties.append("</svg>")
    return "\n".join(parties)


# ==========================================================================
# Figure 11 — Le déroulement du stage en quatre itérations
# ==========================================================================

def figure_calendrier() -> str:
    """Calendrier des quatre itérations, et jalons associés."""
    L, H = 1280, 620
    x0, largeur = 250, 940
    semaines = 8

    sprints = [
        ("Sprint 1", "Socle et sécurité", 0, 2, PRIMAIRE, BLEUCLAIR,
         "Modèle de données &#183; authentification &#183; contrôle d'accès"),
        ("Sprint 2", "Interface et parcours", 2, 2, SECONDAIRE, SARCCLAIR,
         "Écrans des trois profils &#183; dépôt &#183; suivi"),
        ("Sprint 3", "Analyse et notation", 4, 2, ACCENT, AMBRECLAIR,
         "Lecture des documents &#183; moteur à cinq composantes"),
        ("Sprint 4", "Industrialisation", 6, 2, SUCCES, VERTCLAIR,
         "Apprentissage &#183; intégration continue &#183; déploiement"),
    ]

    parties = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{L}" height="{H}" '
        f'viewBox="0 0 {L} {H}">',
        f'  <rect width="{L}" height="{H}" fill="{BLANC}"/>',
        f'  <text x="40" y="46" font-family="Helvetica" font-size="18" '
        f'font-weight="bold" fill="{ENCRE}">Déroulement du stage — '
        f'quatre itérations de deux semaines</text>',
    ]

    # Graduation en semaines.
    for s in range(semaines + 1):
        x = x0 + largeur * s / semaines
        parties.append(
            f'  <line x1="{x:.0f}" y1="86" x2="{x:.0f}" y2="470" '
            f'stroke="{GRISCLAIR}" stroke-width="1.5"/>'
        )
        if s < semaines:
            parties.append(
                f'  <text x="{x + largeur / semaines / 2:.0f}" y="78" '
                f'text-anchor="middle" font-family="Helvetica" font-size="12" '
                f'fill="{NEUTRE}">S{s + 1}</text>'
            )

    for i, (nom, objet, debut, duree, trait, fond, livrable) in enumerate(sprints):
        y = 104 + i * 92
        xa = x0 + largeur * debut / semaines
        xb = x0 + largeur * (debut + duree) / semaines
        parties.append(f'''
  <text x="{x0 - 18}" y="{y + 26}" text-anchor="end" font-family="Helvetica"
        font-size="14" font-weight="bold" fill="{ENCRE}">{nom}</text>
  <text x="{x0 - 18}" y="{y + 46}" text-anchor="end" font-family="Helvetica"
        font-size="11.5" fill="{NEUTRE}">{objet}</text>
  <rect x="{xa:.0f}" y="{y}" width="{xb - xa:.0f}" height="40" rx="8"
        fill="{fond}" stroke="{trait}" stroke-width="2.5"/>
  <text x="{(xa + xb) / 2:.0f}" y="{y + 26}" text-anchor="middle"
        font-family="Helvetica" font-size="13" font-weight="bold"
        fill="{ENCRE}">{objet}</text>
  <circle cx="{xb:.0f}" cy="{y + 40}" r="7" fill="{trait}"/>
  <text x="{xa + 4:.0f}" y="{y + 62}" font-family="Helvetica" font-size="11.5"
        fill="{NEUTRE}">{livrable}</text>''')

    parties.append(f'''
  <line x1="{x0}" y1="492" x2="{x0 + largeur}" y2="492" stroke="{ENCRE}"
        stroke-width="2"/>
  <text x="{x0}" y="524" font-family="Helvetica" font-size="12"
        fill="{ENCRE}">début du stage</text>
  <text x="{x0 + largeur}" y="524" text-anchor="end" font-family="Helvetica"
        font-size="12" fill="{ENCRE}">remise et démonstration</text>
  <rect x="40" y="548" width="1200" height="46" rx="8" fill="{GRISCLAIR}"
        stroke="{NEUTRE}" stroke-width="1.5"/>
  <text x="60" y="577" font-family="Helvetica" font-size="12.5" fill="{ENCRE}">Le disque en fin de barre marque la clôture d'une itération : un rapport d'avancement écrit, et une démonstration de ce qui fonctionne réellement.</text>''')

    parties.append("</svg>")
    return "\n".join(parties)


# ==========================================================================
# Point d'entrée
# ==========================================================================

FIGURES = {
    "cas_utilisation": ("svg", figure_cas_utilisation),
    "sequence_analyse": ("svg", figure_sequence),
    "activite_rg01": ("dot", figure_activite),
    "classes": ("dot-modele", figure_classes),
    "schema_relationnel": ("dot-modele", figure_schema),
    "architecture_composants": ("dot", figure_composants),
    "deploiement": ("dot", figure_deploiement),
    "chaine_cicd": ("dot", figure_cicd),
    "organigramme": ("dot", figure_organigramme),
    "tracabilite": ("svg", figure_tracabilite),
    "temps_pipeline": ("svg", figure_temps_pipeline),
    "calendrier_sprints": ("svg", figure_calendrier),
}


def main(argv):
    demandees = argv[1:] or list(FIGURES)
    inconnues = [n for n in demandees if n not in FIGURES]
    if inconnues:
        print(f"Figure inconnue : {', '.join(inconnues)}", file=sys.stderr)
        print(f"Disponibles : {', '.join(FIGURES)}", file=sys.stderr)
        return 2

    tables = None
    if any(FIGURES[n][0] == "dot-modele" for n in demandees):
        tables = metadonnees()

    for nom in demandees:
        genre, fabrique = FIGURES[nom]
        source = fabrique(tables) if genre == "dot-modele" else fabrique()
        chemin = (rendre_svg if genre == "svg" else rendre_dot)(f"fig_{nom}", source)
        taille = os.path.getsize(chemin) // 1024
        print(f"  fig_{nom}.png  ({taille} Kio)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
