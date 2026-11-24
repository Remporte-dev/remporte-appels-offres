"""Copie modifiable d'une pièce Word ou Excel au format 97-2003."""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from remporte import ecritures, espace, lecture, livraison

_EXTENSIONS = {".xls": ".xlsx", ".doc": ".docx"}
_CHEMINS_SOFFICE = (
    Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "LibreOffice/program/soffice.exe",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    / "LibreOffice/program/soffice.exe",
)
_CONSEIL = ("Pour une conversion fidèle, installez LibreOffice ou enregistrez le fichier "
            "au nouveau format depuis Excel ou Word.")
_PERTE_XLS = ("les formules ne sont pas converties : chaque cellule garde sa dernière valeur "
              "calculée (les valeurs, cellules fusionnées, largeurs de colonnes, formats de "
              "nombre et gras sont repris)")
_PERTE_DOC = ("la mise en page, les tableaux et les cases à cocher ne sont pas conservés : "
              "seul le texte, paragraphe par paragraphe, est repris")


@dataclass
class Resultat:
    fichier: Path
    methode: str
    pertes: str = ""
    conseil: str = ""


def convertir(source: Path, sortie: Path | None = None, *, lot: str | None = None) -> Resultat:
    if not source.is_file():
        raise espace.Erreur(f"Fichier introuvable : {source}.")
    ancien = source.suffix.lower()
    moderne = _EXTENSIONS.get(ancien)
    if moderne is None:
        raise espace.Erreur("La conversion concerne les anciens formats .doc et .xls "
                            f"(reçu : {ancien or 'fichier sans extension'}).")
    if sortie is not None:
        if lot is not None:
            raise espace.Erreur("--lot et --sortie ne se combinent pas.")
        if sortie.suffix.lower() != moderne:
            raise espace.Erreur(f"La copie d'un {ancien} se termine par {moderne}.")
    else:
        dossier = espace.trouver_dossier(source.parent)
        if dossier is not None:
            parent = livraison.chemin_dossier_lot(dossier, lot)
        elif lot is not None:
            raise espace.Erreur("--lot ne s'utilise que dans un dossier de réponse.")
        else:
            parent = source.parent
        sortie = parent / (source.stem + moderne)

    soffice = _trouver_soffice()
    if soffice is not None:
        contenu = _convertir_avec_soffice(soffice, source, moderne)
        if contenu is not None:
            return Resultat(ecritures.ecrire_copie(sortie, contenu), "LibreOffice")
    if ancien == ".xls":
        contenu, pertes = _xls_vers_xlsx(source), _PERTE_XLS
    else:
        contenu, pertes = _doc_vers_docx(source), _PERTE_DOC
    return Resultat(ecritures.ecrire_copie(sortie, contenu), "conversion simplifiée", pertes, _CONSEIL)


def _trouver_soffice() -> str | None:
    for nom in ("soffice", "libreoffice"):
        if trouve := shutil.which(nom):
            return trouve
    for chemin in _CHEMINS_SOFFICE:
        if chemin.is_file():
            return str(chemin)
    return None


def _convertir_avec_soffice(soffice: str, source: Path, extension: str) -> bytes | None:
    try:
        with tempfile.TemporaryDirectory(prefix="remporte-convertir-") as travail:
            dossier = Path(travail)
            commande = [
                soffice, "--headless", "--norestore",
                f"-env:UserInstallation={(dossier / 'profil').as_uri()}",
                "--convert-to", extension[1:], "--outdir", travail, str(source.absolute()),
            ]
            subprocess.run(commande, capture_output=True, timeout=120, check=True)
            return (dossier / (source.stem + extension)).read_bytes()
    except (OSError, subprocess.SubprocessError):
        return None


def _xls_vers_xlsx(source: Path) -> bytes:
    import xlrd
    from openpyxl import Workbook

    sortie = Workbook()
    try:
        with xlrd.open_workbook(str(source), formatting_info=True, logfile=io.StringIO()) as classeur:
            if classeur.nsheets:
                sortie.remove(sortie.active)
            for feuille in classeur.sheets():
                nom = _nom_feuille(feuille.name, sortie.sheetnames)
                _copier_feuille_xls(feuille, classeur, sortie.create_sheet(nom))
    except Exception:  # noqa: BLE001 — xlrd peut lever sur un classeur endommagé
        raise espace.Erreur(f"{source.name} ne peut pas être lu (classeur Excel illisible) : "
                            "conversion impossible sans LibreOffice.") from None
    contenu = io.BytesIO()
    sortie.save(contenu)
    return contenu.getvalue()


def _nom_feuille(nom: str, existants: list[str]) -> str:
    propre = re.sub(r"[\\/*?:\[\]]", "-", nom) or "Feuille"
    existants_min = {titre.lower() for titre in existants}
    titre = propre[:31]
    rang = 2
    while titre.lower() in existants_min:
        suffixe = f" ({rang})"
        titre = propre[:31 - len(suffixe)] + suffixe
        rang += 1
    return titre


def _copier_feuille_xls(feuille, classeur, destination) -> None:
    import xlrd
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    for colonne, info in feuille.colinfo_map.items():
        destination.column_dimensions[get_column_letter(colonne + 1)].width = info.width / 256
    gras = Font(bold=True)
    for rang, ligne in enumerate(feuille.get_rows(), start=1):
        for colonne, cellule in enumerate(ligne, start=1):
            if cellule.ctype == xlrd.XL_CELL_EMPTY:
                continue
            valeur = lecture.valeur_xls(cellule, classeur.datemode)
            cible = destination.cell(row=rang, column=colonne, value=valeur)
            if cellule.ctype == xlrd.XL_CELL_TEXT:
                cible.data_type = "s"  # conserve le texte, même s'il commence par « = »
            elif cellule.ctype == xlrd.XL_CELL_ERROR:
                cible.data_type = "e"
            if cellule.xf_index is not None and cellule.xf_index >= 0:
                xf = classeur.xf_list[cellule.xf_index]
                if classeur.font_list[xf.font_index].bold:
                    cible.font = gras
                fmt = classeur.format_map.get(xf.format_key)
                if fmt is not None and fmt.format_str != "General":
                    cible.number_format = fmt.format_str
    for rlo, rhi, clo, chi in feuille.merged_cells:
        destination.merge_cells(start_row=rlo + 1, start_column=clo + 1,
                                end_row=rhi, end_column=chi)


def _doc_vers_docx(source: Path) -> bytes:
    from docx import Document

    lecture_doc = lecture.convertir(source)
    if lecture_doc.statut != "ok":
        raise espace.Erreur(f"{source.name} ne peut pas être lu ({lecture_doc.motif}) : "
                            "conversion impossible sans LibreOffice.")
    document = Document()
    for paragraphe in lecture_doc.texte.split("\n\n"):
        document.add_paragraph(paragraphe)
    contenu = io.BytesIO()
    document.save(contenu)
    return contenu.getvalue()
