"""Génération de CV au format PDF pour le jeu de démonstration.

Le fichier produit est un PDF valide contenant une véritable couche texte,
de sorte que la chaîne d'analyse le traite exactement comme un document
déposé par un candidat — sans passer par la reconnaissance optique.

L'écriture se fait sans dépendance externe : le format PDF est suffisamment
simple pour un document textuel, et cela évite d'alourdir l'image du service
pour un besoin limité à la démonstration.
"""

LARGEUR_PAGE = 595   # A4 en points
HAUTEUR_PAGE = 842
MARGE = 56
INTERLIGNE = 14


def _echapper(texte):
    """Protège les caractères réservés de la syntaxe PDF."""
    return texte.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _vers_latin1(texte):
    """Le jeu de caractères WinAnsi ne couvre pas tout l'Unicode.

    Les caractères absents sont remplacés par un équivalent lisible plutôt
    que supprimés, afin que le texte reste analysable.
    """
    remplacements = {
        "–": "-", "—": "-", "'": "'", "'": "'", """: '"', """: '"',
        "…": "...", "•": "-", "≥": ">=", "≤": "<=", " ": " ", "\xa0": " ",
    }
    for source, cible in remplacements.items():
        texte = texte.replace(source, cible)
    return texte.encode("latin-1", errors="replace").decode("latin-1")


def _flux_page(lignes):
    """Construit le flux de contenu d'une page."""
    morceaux = ["BT", "/F1 10 Tf", f"{INTERLIGNE} TL",
                f"1 0 0 1 {MARGE} {HAUTEUR_PAGE - MARGE} Tm"]
    for ligne in lignes:
        contenu = _echapper(_vers_latin1(ligne))
        # Les titres de section sont mis en evidence
        gras = ligne.isupper() and len(ligne) < 40 and ligne.strip()
        morceaux.append(f"/{'F2' if gras else 'F1'} {11 if gras else 10} Tf")
        morceaux.append(f"({contenu}) Tj")
        morceaux.append("T*")
    morceaux.append("ET")
    return "\n".join(morceaux)


def ecrire_cv_pdf(chemin, texte):
    """Écrit `texte` dans un PDF paginé à l'emplacement indiqué."""
    lignes_par_page = (HAUTEUR_PAGE - 2 * MARGE) // INTERLIGNE
    toutes = texte.splitlines() or [""]
    pages = [
        toutes[i:i + lignes_par_page]
        for i in range(0, len(toutes), lignes_par_page)
    ]

    objets = []          # corps de chaque objet, index = numero - 1
    nb_pages = len(pages)

    # 1 : catalogue, 2 : arbre des pages, 3 et 4 : polices
    ids_pages = [5 + 2 * i for i in range(nb_pages)]
    objets.append("<< /Type /Catalog /Pages 2 0 R >>")
    objets.append(
        "<< /Type /Pages /Kids ["
        + " ".join(f"{i} 0 R" for i in ids_pages)
        + f"] /Count {nb_pages} >>"
    )
    police = "<< /Type /Font /Subtype /Type1 /BaseFont /{} /Encoding /WinAnsiEncoding >>"
    objets.append(police.format("Helvetica"))
    objets.append(police.format("Helvetica-Bold"))

    for index, lignes in enumerate(pages):
        id_page = 5 + 2 * index
        id_flux = id_page + 1
        objets.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {LARGEUR_PAGE} {HAUTEUR_PAGE}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {id_flux} 0 R >>"
        )
        flux = _flux_page(lignes)
        objets.append(f"<< /Length {len(flux)} >>\nstream\n{flux}\nendstream")

    # Assemblage avec la table de references croisees
    sortie = bytearray(b"%PDF-1.4\n")
    positions = []
    for numero, corps in enumerate(objets, start=1):
        positions.append(len(sortie))
        sortie += f"{numero} 0 obj\n{corps}\nendobj\n".encode("latin-1")

    debut_xref = len(sortie)
    sortie += f"xref\n0 {len(objets) + 1}\n".encode("latin-1")
    sortie += b"0000000000 65535 f \n"
    for position in positions:
        sortie += f"{position:010d} 00000 n \n".encode("latin-1")
    sortie += (
        f"trailer\n<< /Size {len(objets) + 1} /Root 1 0 R >>\n"
        f"startxref\n{debut_xref}\n%%EOF\n"
    ).encode("latin-1")

    with open(chemin, "wb") as fichier:
        fichier.write(sortie)

    return chemin
