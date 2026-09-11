"""Tests de l'extraction du texte : nettoyage et redressement des glyphes.

Certains générateurs de PDF simulent le gras en dessinant deux fois le même
glyphe. La couche texte livre alors chaque lettre en double — « Aymen
Benrbib » devient « AAyymmeenn BBeennrrbbiibb ». Le défaut est silencieux :
le nom lu ne correspond plus à celui du compte et la candidature est signalée
comme suspecte alors qu'elle est parfaitement régulière.
"""
import pytest

from app.services import extraction


# ----------------------- Redressement du doublement -----------------------

def test_un_nom_aux_lettres_redoublees_est_redresse():
    assert extraction.corriger_doublement("AAyymmeenn BBeennrrbbiibb") == "Aymen Benrbib"


def test_un_en_tete_de_rubrique_redouble_est_redresse():
    assert extraction.corriger_doublement("FFOORRMMAATTIIOONN") == "FORMATION"


def test_un_texte_normal_n_est_pas_modifie():
    original = "Ingénieur en Systèmes d'Information & Transformation Digitale"
    assert extraction.corriger_doublement(original) == original


def test_les_doubles_lettres_legitimes_sont_preservees():
    """« bookkeeper » n'est pas « bokeper » : le seuil protège ces mots."""
    original = "bookkeeper committee aardvark успешно"
    assert extraction.corriger_doublement(original) == original


def test_le_redressement_s_applique_ligne_par_ligne():
    texte = "AAyymmeenn BBeennrrbbiibb\nRabat, Maroc\nFFOORRMMAATTIIOONN"
    assert extraction.corriger_doublement(texte).splitlines() == [
        "Aymen Benrbib",
        "Rabat, Maroc",
        "FORMATION",
    ]


def test_un_mot_isole_redouble_dans_une_phrase_reste_intact():
    """Un seul mot suspect ne suffit pas : la ligne reste telle quelle."""
    original = "Le protocole SSTT est décrit dans le rapport annuel de synthèse"
    assert extraction.corriger_doublement(original) == original


def test_le_nettoyage_redresse_aussi_le_doublement():
    assert extraction.nettoyer("AAyymmeenn   BBeennrrbbiibb") == "Aymen Benrbib"


# ----------------------- Nettoyage -----------------------

def test_les_mots_coupes_en_fin_de_ligne_sont_recolles():
    assert "transformation" in extraction.nettoyer("trans-\nformation")


def test_les_sauts_de_ligne_multiples_sont_ramenes_a_deux():
    assert extraction.nettoyer("a\n\n\n\n\nb") == "a\n\nb"


# ----------------------- Contenu hors du cadre de la page -----------------------
#
# Un CV trop long pour son format conserve ses lignes en trop dans la couche
# texte, posees sous le bord de la page. Elles n'apparaissent ni a l'ecran ni a
# l'impression, mais un extracteur naif les lit comme les autres : le profil se
# garnit alors de competences et de langues que le recruteur ne retrouve nulle
# part dans le document affiche a cote. Le meme hors-champ sert aussi a bourrer
# un CV de mots-cles invisibles.


def _pdf_minimal(chemin, lignes):
    """Écrit un PDF d'une page. `lignes` : des couples (y, texte).

    Construit a la main plutot qu'avec une bibliotheque de generation : le
    projet n'en embarque aucune, et le test doit pouvoir placer du texte a une
    ordonnee negative — sous le bord inferieur de la page — ce qu'aucune
    bibliotheque de mise en page ne propose.
    """
    contenu = "BT /F1 11 Tf\n" + "".join(
        f"1 0 0 1 50 {y} Tm ({texte}) Tj\n" for y, texte in lignes
    ) + "ET"
    objets = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(contenu)} >>\nstream\n{contenu}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    sortie = bytearray(b"%PDF-1.4\n")
    decalages = []
    for numero, objet in enumerate(objets, start=1):
        decalages.append(len(sortie))
        sortie += f"{numero} 0 obj\n{objet}\nendobj\n".encode("latin-1")

    debut_table = len(sortie)
    sortie += f"xref\n0 {len(objets) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for decalage in decalages:
        sortie += f"{decalage:010d} 00000 n \n".encode("latin-1")
    sortie += (
        f"trailer\n<< /Size {len(objets) + 1} /Root 1 0 R >>\n"
        f"startxref\n{debut_table}\n%%EOF\n"
    ).encode("latin-1")

    chemin.write_bytes(bytes(sortie))
    return chemin


def test_le_texte_pose_sous_le_bord_de_la_page_est_ecarte(tmp_path):
    """Ce que le recruteur ne peut pas voir ne doit pas nourrir le profil."""
    pytest.importorskip("pdfplumber")
    chemin = _pdf_minimal(
        tmp_path / "deborde.pdf",
        # Le texte visible depasse le seuil d'exploitabilite : sans cela,
        # l'extraction basculerait sur la reconnaissance optique et le test
        # ne mesurerait plus ce qu'il vise.
        [(700, "COMPETENCES TECHNIQUES"),
         (680, "Docker, Kubernetes, GitHub Actions, Linux, Python, SQL, Java"),
         (660, "Frameworks : React.js, Angular, Laravel, Spring Boot, Pandas"),
         (-40, "LANGUES"), (-60, "Arabe (Maternel) - Francais (Courant)")],
    )
    resultat = extraction.extraire_texte(str(chemin))

    assert "Docker" in resultat.texte
    assert "LANGUES" not in resultat.texte
    assert "Maternel" not in resultat.texte


def test_le_volume_ecarte_hors_page_est_remonte(tmp_path):
    """L'interface doit pouvoir le dire : un rejet silencieux est un piège."""
    pytest.importorskip("pdfplumber")
    chemin = _pdf_minimal(
        tmp_path / "deborde.pdf",
        [(700, "EXPERIENCE PROFESSIONNELLE"),
         (680, "Stagiaire developpeur fullstack chez Exemple SARL en 2025"),
         (660, "Developpement d'une plateforme de vente en ligne, Laravel"),
         (-50, "mots-cles invisibles")],
    )
    resultat = extraction.extraire_texte(str(chemin))

    assert resultat.hors_page == len("mots-cles invisibles")
    assert resultat.to_dict()["horsPage"] == resultat.hors_page


def test_un_document_qui_tient_dans_sa_page_ne_perd_rien(tmp_path):
    pytest.importorskip("pdfplumber")
    chemin = _pdf_minimal(
        tmp_path / "normal.pdf",
        [(700, "COMPETENCES TECHNIQUES"),
         (680, "Docker, Kubernetes, GitHub Actions, Linux, Python, SQL, Java"),
         (660, "Frameworks : React.js, Angular, Laravel, Spring Boot, Pandas"),
         (640, "LANGUES : Arabe (Maternel), Francais (Courant)")],
    )
    resultat = extraction.extraire_texte(str(chemin))

    assert resultat.hors_page == 0
    assert "LANGUES" in resultat.texte
