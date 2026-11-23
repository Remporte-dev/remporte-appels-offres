"""Sigles et numéros courts dans la recherche (lot B, 2.4).

La requête FTS jetait les termes de deux lettres ou moins : chercher « AE »,
« RC » ou « 12 » ne trouvait rien, alors que ces sigles et numéros sont
partout dans un DCE. Contrat : les termes d'au moins deux caractères sont
cherchés. (Le fermé va jusqu'à chercher les termes d'un seul caractère : ce
point n'est pas exigé ici, voir le rapport.)

Repris du fermé : tests/test_recherche.py::test_recherche_sigle_et_numero_courts,
étendu à AE et 12.
"""

from __future__ import annotations

from pathlib import Path

from remporte import recherche


def test_sigles_et_numeros_courts_trouves(tmp_path: Path):
    texte_ae = tmp_path / ".remporte" / "texte" / "AE.pdf.md"
    texte_ae.parent.mkdir(parents=True)
    texte_ae.write_text(
        "Acte d'engagement AE, Entreprise Exemple, 12 pages.", encoding="utf-8")
    texte_rc = tmp_path / ".remporte" / "texte" / "RC.pdf.md"
    texte_rc.write_text("RC lot 6. Câble de 25 mm².", encoding="utf-8")
    recherche.indexer_dce(tmp_path)

    assert [r["piece"] for r in recherche.chercher_dce(tmp_path, "AE")] == ["AE.pdf"]
    assert [r["piece"] for r in recherche.chercher_dce(tmp_path, "RC")] == ["RC.pdf"]
    assert [r["piece"] for r in recherche.chercher_dce(tmp_path, "12")] == ["AE.pdf"]
    assert [r["piece"] for r in recherche.chercher_dce(tmp_path, "25")] == ["RC.pdf"]
    assert [r["piece"] for r in recherche.chercher_dce(tmp_path, "RC lot 6")] == ["RC.pdf"]
