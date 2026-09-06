"""Garde les promesses de build_banner.py.

Le coeur de ce depot n'est pas de dessiner joli : c'est qu'un compteur affiche
soit un chiffre vrai, soit rien. Et que la banniere reste lisible chez un moteur
qui n'anime pas. Ces deux promesses etaient tenues a la main jusqu'ici.
"""

import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import build_banner  # noqa: E402


def elements(doc, balise=None):
    """Parcourt le SVG. ElementTree prefixe les balises du namespace, d'ou le split."""
    for el in ElementTree.fromstring(doc).iter():
        if balise is None or el.tag.rsplit("}", 1)[-1] == balise:
            yield el


def titre_et_glyphes(doc):
    """Rend les <text> du titre, ceux qui portent la bascule brouillage/lettre."""
    return [t for t in elements(doc, "text") if t.get("font-size") == "44"]


def test_compteurs_rendus_sur_deux_chiffres():
    doc = build_banner.svg(50, 2, 9)
    for attendu in (">50<", ">02<", ">09<"):
        assert attendu in doc, f"compteur absent : {attendu}"


def test_svg_bien_forme():
    ElementTree.fromstring(build_banner.svg(50, 2, 9))


def test_aucune_ressource_chargee_depuis_le_reseau():
    """Camo sert la banniere avec `default-src 'none'` : tout appel sortant meurt.

    On ne cherche pas la chaine "http" betement : `xmlns` est un namespace XML,
    que personne ne va chercher sur le reseau, et `url(#scan)` pointe un degrade
    interne. Ce qui compte, c'est qu'aucun ATTRIBUT ne demande une ressource
    distante.
    """
    doc = build_banner.svg(50, 2, 9)
    assert "@import" not in doc and "<script" not in doc

    for el in elements(doc):
        for nom, valeur in el.attrib.items():
            assert "//" not in valeur, (
                f"<{el.tag} {nom}> pointe hors du fichier : {valeur}")


def test_titre_lisible_quand_rien_ne_s_anime():
    """Un moteur sans SMIL doit montrer WOLDENMN, jamais le brouillage fige.

    Les attributs `opacity` portent l'etat de REPOS et les <animate> les
    surchargent. Inverser les deux jeux fige le titre sur des glyphes illisibles,
    et le defaut ne se voit pas chez un moteur qui anime, c'est-a-dire partout ou
    on regarde.
    """
    lettres = set(build_banner.TITRE)
    au_repos = []
    for noeud in titre_et_glyphes(build_banner.svg(50, 2, 9)):
        if noeud.get("opacity") != "0":
            au_repos.append(noeud.text or "")

    assert au_repos, "aucun <text> visible au repos : le titre serait invisible"
    assert set(au_repos) <= lettres, (
        f"un glyphe de brouillage est visible au repos : {set(au_repos) - lettres}")
    assert "".join(au_repos) == build_banner.TITRE, (
        f"titre au repos = {''.join(au_repos)!r}, attendu {build_banner.TITRE!r}")


def test_refus_d_ecrire_quand_l_api_est_muette(tmp_path, monkeypatch, capsys):
    """API injoignable : code de sortie non nul, et surtout aucune ecriture."""
    def api_muette():
        raise RuntimeError("gh introuvable")

    monkeypatch.setattr(build_banner, "compte_depuis_api", api_muette)
    monkeypatch.setattr(sys, "argv", ["build_banner.py"])
    monkeypatch.chdir(tmp_path)
    (tmp_path / "assets").mkdir()

    code = build_banner.main()

    assert code == 1, "un echec d'API doit rendre un code non nul"
    assert not (tmp_path / "assets" / "banner.svg").exists(), (
        "un chiffre faux a ete ecrit alors que l'API etait muette")
    assert "ECHEC" in capsys.readouterr().err


def test_refus_de_compter_zero_depot(monkeypatch):
    """Une reponse vide n'est pas 'zero depot' : c'est un appel qui a echoue."""
    class Reponse:
        returncode = 0
        stdout = "[]"
        stderr = ""

    monkeypatch.setattr(build_banner.subprocess, "run", lambda *_args, **_kwargs: Reponse())
    with pytest.raises(RuntimeError, match="0 depot"):
        build_banner.compte_depuis_api()


def test_mode_offline_ecrit_les_valeurs_donnees(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["build_banner.py", "--offline", "7", "3", "1"])
    monkeypatch.chdir(tmp_path)
    (tmp_path / "assets").mkdir()

    assert build_banner.main() == 0
    ecrit = (tmp_path / "assets" / "banner.svg").read_text(encoding="utf-8")
    assert ">07<" in ecrit and ">03<" in ecrit and ">01<" in ecrit
