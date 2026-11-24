"""Fabriques de pièces de test : PDF minimal en bytes, DOCX, XLSX, ODS, PPTX, ZIP,
pièces OLE2 (.doc Word 97-2003) et accès aux fixtures."""

from __future__ import annotations

import zipfile
from pathlib import Path


def chemin_fixture(nom: str) -> Path:
    """Chemin d'une pièce d'exemple de tests/fixtures/ (fictive, voir LISEZMOI.md)."""
    return Path(__file__).resolve().parent / "fixtures" / nom


# ---------------------------------------------------------------------------
# PDF minimal — construit à la main (objets + xref exacts), lu par pypdfium2
# ---------------------------------------------------------------------------

def ecrire_pdf(chemin: Path, pages: list[str]) -> Path:
    """Petit PDF valide : pages de lignes Helvetica (texte ASCII ; \n = ligne).

    Numérotation : 1 = catalogue, 2 = arbre des pages, 3 = fonte,
    4..3+n = pages, 4+n..3+2n = contenus.
    """
    nb = len(pages)
    objets: dict[int, bytes] = {}
    objets[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{3 + i} 0 R" for i in range(1, nb + 1))
    objets[2] = f"<< /Type /Pages /Kids [{kids}] /Count {nb} >>".encode()
    objets[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    for i in range(1, nb + 1):
        objets[3 + i] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {3 + nb + i} 0 R >>"
        ).encode()
    for i, page in enumerate(pages, start=1):
        commandes = []
        for k, ligne in enumerate(page.split("\n")):
            echappe = (ligne.replace("\\", r"\\")
                       .replace("(", r"\(").replace(")", r"\)"))
            y = 720 - 20 * k
            commandes.append(f"1 0 0 1 72 {y} Tm ({echappe}) Tj")
        flux = (f"BT /F1 14 Tf " + " ".join(commandes) + " ET").encode("latin-1")
        objets[3 + nb + i] = (
            f"<< /Length {len(flux)} >>\nstream\n".encode() + flux + b"\nendstream"
        )

    sortie = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for numero in sorted(objets):
        offsets[numero] = len(sortie)
        sortie += f"{numero} 0 obj\n".encode() + objets[numero] + b"\nendobj\n"
    depart_xref = len(sortie)
    maxi = max(objets) + 1
    sortie += f"xref\n0 {maxi}\n".encode()
    sortie += b"0000000000 65535 f \n"
    for numero in range(1, maxi):
        sortie += f"{offsets[numero]:010d} 00000 n \n".encode()
    sortie += (
        f"trailer\n<< /Size {maxi} /Root 1 0 R >>\n"
        f"startxref\n{depart_xref}\n%%EOF\n"
    ).encode()
    chemin.write_bytes(bytes(sortie))
    return chemin


# ---------------------------------------------------------------------------
# DOCX / XLSX / ODS / PPTX / ZIP
# ---------------------------------------------------------------------------

def fabriquer_docx(chemin: Path) -> Path:
    from docx import Document

    document = Document()
    document.add_heading("Règlement de consultation", 1)
    document.add_paragraph("Objet : AMO pour le musée.")
    document.add_paragraph("Critères de jugement :", style="Normal")
    document.add_paragraph(
        "Le critère valeur technique est noté sur 60 %.", style="List Bullet"
    )
    document.add_paragraph("Le candidat **doit** justifier ses références.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Critère"
    table.cell(0, 1).text = "Pondération"
    table.cell(1, 0).text = "Valeur technique"
    table.cell(1, 1).text = "60 %"
    document.save(str(chemin))
    return chemin


def fabriquer_docx_crt(chemin: Path) -> Path:
    """CRT avec un style dédié « DemandeCandidat » pour la voie par styles."""
    from docx import Document
    from docx.enum.style import WD_STYLE_TYPE

    document = Document()
    document.add_heading("Cahier des réponses", 1)
    style = document.styles.add_style("DemandeCandidat", WD_STYLE_TYPE.PARAGRAPH)
    document.add_paragraph(
        "Le candidat décrit son organisation.", style="DemandeCandidat"
    )
    document.add_paragraph(
        "Le candidat fournit trois références comparables.",
        style="DemandeCandidat",
    )
    document.add_paragraph(
        "Le candidat justifie ses moyens humains.", style="DemandeCandidat"
    )
    document.add_paragraph("Présentation générale de l'offre.")
    document.save(str(chemin))
    return chemin


def fabriquer_xlsx(chemin: Path) -> Path:
    from openpyxl import Workbook

    classeur = Workbook()
    feuille = classeur.active
    feuille.title = "BPU"
    feuille.append(["Désignation", "Quantité", "Prix"])
    feuille.append(["Prestation A", 3, None])
    feuille2 = classeur.create_sheet("DQE")
    feuille2.append(["Poste", "Montant"])
    feuille2.append(["Lot 1", 1200])
    classeur.save(str(chemin))
    return chemin


def fabriquer_ods(chemin: Path) -> Path:
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.table import Table, TableCell, TableRow
    from odf.text import P

    document = OpenDocumentSpreadsheet()
    table = Table(name="Feuille1")
    for ligne in (["Désignation", "Prix"], ["Prestation X", ""]):
        tr = TableRow()
        for valeur in ligne:
            tc = TableCell(valuetype="string")
            tc.addElement(P(text=valeur))
            tr.addElement(tc)
        table.addElement(tr)
    document.spreadsheet.addElement(table)
    document.save(str(chemin))
    return chemin


def fabriquer_pptx(chemin: Path) -> Path:
    ns = (
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    )
    diapo = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<p:sld {ns}><p:cSld><p:spTree>"
        "<a:p><a:r><a:t>Présentation de l'entreprise</a:t></a:r></a:p>"
        "<a:p><a:r><a:t>Créée en 2010</a:t></a:r></a:p>"
        "</p:spTree></p:cSld></p:sld>"
    )
    with zipfile.ZipFile(chemin, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("ppt/slides/slide1.xml", diapo)
    return chemin


def fabriquer_zip(chemin: Path, contenus: dict[str, bytes | str],
                  zips_internes: dict[str, dict[str, str]] | None = None) -> Path:
    """ZIP avec fichiers plats et, si demandé, des ZIP dans le ZIP."""
    with zipfile.ZipFile(chemin, "w") as zf:
        for nom, contenu in contenus.items():
            if isinstance(contenu, str):
                contenu = contenu.encode("utf-8")
            zf.writestr(nom, contenu)
        for nom_zip, fichiers in (zips_internes or {}).items():
            tampon = Path(str(chemin) + ".interne.zip")
            with zipfile.ZipFile(tampon, "w") as zi:
                for nom, contenu in fichiers.items():
                    zi.writestr(nom, contenu.encode("utf-8"))
            zf.writestr(nom_zip, tampon.read_bytes())
            tampon.unlink()
    return chemin


# ---------------------------------------------------------------------------
# OLE2 (.doc Word 97-2003) : conteneur minimal et FIB
# ---------------------------------------------------------------------------

def ecrire_ole(chemin: Path, flux: dict[str, bytes]) -> Path:
    """Fichier OLE2 (CDF V2) minimal, lisible par olefile : un flux par nom.

    Chaque flux est complété à 4 096 octets pour rester un flux ordinaire
    (pas de ministream). Un secteur de FAT, un de répertoire, puis les données.
    """
    SECTEUR = 512
    FIN = 0xFFFFFFFE
    LIBRE = 0xFFFFFFFF

    contenu = []  # secteurs de données (après FAT et répertoire)
    chaines: dict[str, tuple[int, int]] = {}  # nom → (début, taille)
    for nom, donnees in flux.items():
        donnees = donnees + b"\x00" * (-len(donnees) % 4096)
        if len(donnees) < 4096:
            donnees = donnees.ljust(4096, b"\x00")
        debut = 2 + len(contenu)
        chaines[nom] = (debut, len(donnees))
        for rang in range(0, len(donnees), SECTEUR):
            contenu.append(donnees[rang:rang + SECTEUR])

    fat = [LIBRE] * 128
    fat[0] = 0xFFFFFFFD  # le FAT lui-même
    fat[1] = FIN          # le répertoire
    for rang in range(len(contenu)):
        fin_du_flux = (rang + 1) % 8 == 0 or rang == len(contenu) - 1
        fat[2 + rang] = FIN if fin_du_flux else 2 + rang + 1

    def entree(nom: str, type_: int, enfant: int | None = None,
               frere: int | None = None, debut: int | None = None,
               taille: int = 0) -> bytes:
        nom_utf16 = nom.encode("utf-16-le") + b"\x00\x00"
        sortie = nom_utf16.ljust(64, b"\x00")
        sortie += len(nom_utf16).to_bytes(2, "little")
        sortie += bytes([type_, 1])  # type (5 = racine, 2 = flux), noir
        sortie += (0xFFFFFFFF).to_bytes(4, "little")          # frère gauche
        sortie += (frere if frere is not None else 0xFFFFFFFF).to_bytes(4, "little")  # frère droit
        sortie += (enfant if enfant is not None else 0xFFFFFFFF).to_bytes(4, "little")
        sortie += b"\x00" * 16                                 # CLSID
        sortie += b"\x00" * 4                                  # état
        sortie += b"\x00" * 16                                 # création, modification
        sortie += (debut if debut is not None else FIN).to_bytes(4, "little")
        sortie += taille.to_bytes(8, "little")
        assert len(sortie) == 128, len(sortie)
        return sortie

    noms = sorted(chaines)
    repertoire = entree("Root Entry", 5, enfant=1)
    for rang, nom in enumerate(noms):
        debut, taille = chaines[nom]
        # les flux sont les enfants de la racine, chaînés en frères droits
        frere = rang + 2 if rang + 1 < len(noms) else None
        repertoire += entree(nom, 2, frere=frere, debut=debut, taille=taille)
    repertoire = repertoire.ljust(SECTEUR, b"\x00")

    entete = bytearray(SECTEUR)
    entete[0:8] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    entete[0x18:0x1A] = (0x003E).to_bytes(2, "little")
    entete[0x1A:0x1C] = (3).to_bytes(2, "little")
    entete[0x1C:0x1E] = (0xFFFE).to_bytes(2, "little")
    entete[0x1E:0x20] = (9).to_bytes(2, "little")
    entete[0x20:0x22] = (6).to_bytes(2, "little")
    entete[0x28:0x2C] = (0).to_bytes(4, "little")   # secteurs de répertoire (0 en v3)
    entete[0x2C:0x30] = (1).to_bytes(4, "little")   # un secteur de FAT
    entete[0x30:0x34] = (1).to_bytes(4, "little")   # répertoire au secteur 1
    entete[0x38:0x3C] = (4096).to_bytes(4, "little")
    entete[0x3C:0x40] = FIN.to_bytes(4, "little")   # pas de mini-FAT
    entete[0x40:0x44] = (0).to_bytes(4, "little")
    entete[0x44:0x48] = FIN.to_bytes(4, "little")   # pas de DIFAT
    entete[0x48:0x4C] = (0).to_bytes(4, "little")
    entete[0x4C:0x50] = (0).to_bytes(4, "little")   # FAT au secteur 0
    for rang in range(1, 109):
        entete[0x4C + 4 * rang:0x50 + 4 * rang] = LIBRE.to_bytes(4, "little")

    fat_brut = b"".join(valeur.to_bytes(4, "little") for valeur in fat)
    chemin.write_bytes(bytes(entete) + fat_brut + repertoire + b"".join(contenu))
    return chemin


def fabriquer_fib_word(w_ident: int, n_fib: int, drapeaux: int = 0) -> bytes:
    """Flux WordDocument de 4 096 octets réduit à sa signature FIB, pour tester
    les refus (Word 6, document chiffré, signature inconnue)."""
    fib = bytearray(4096)
    fib[0:2] = w_ident.to_bytes(2, "little")
    fib[2:4] = n_fib.to_bytes(2, "little")
    fib[0x0A:0x0C] = drapeaux.to_bytes(2, "little")
    return bytes(fib)


def fabriquer_doc_minimal(chemin: Path, texte: str) -> Path:
    """Document Word 97-2003 minimal et lisible : FIB, table des pièces (CLX)
    dans le flux 1Table, texte en cp1252 à l'octet 0x800 du flux WordDocument.

    Un \r dans le texte sépare deux paragraphes.
    """
    brut = texte.encode("cp1252")
    fib = bytearray(4096)
    fib[0x00:0x02] = (0xA5EC).to_bytes(2, "little")   # wIdent
    fib[0x02:0x04] = (0x00C1).to_bytes(2, "little")   # nFib : Word 97
    fib[0x0A:0x0C] = (0x0200).to_bytes(2, "little")   # fWhichTblStm : table 1Table
    fib[0x4C:0x50] = len(texte).to_bytes(4, "little")  # ccpText
    fib[0x98:0x9A] = (93).to_bytes(2, "little")        # cbRgFcLcb
    # CLX : clxt 0x02, taille du PlcPcd, puis PlcPcd = CP 0, CP n, un PCD.
    # fc = (0x800 × 2) | 0x40000000 : texte compressé (cp1252) à fc / 2.
    fc = (0x800 * 2) | 0x40000000
    plc = (0).to_bytes(4, "little") + len(texte).to_bytes(4, "little")
    plc += (0).to_bytes(2, "little") + fc.to_bytes(4, "little") + (0).to_bytes(2, "little")
    clx = b"\x02" + len(plc).to_bytes(4, "little") + plc
    fc_clx = 0x9A + 33 * 8
    fib[fc_clx:fc_clx + 4] = (0).to_bytes(4, "little")       # fcClx : début du flux 1Table
    fib[fc_clx + 4:fc_clx + 8] = len(clx).to_bytes(4, "little")  # lcbClx : taille du CLX
    fib[0x800:0x800 + len(brut)] = brut
    return ecrire_ole(chemin, {"WordDocument": bytes(fib), "1Table": clx})
