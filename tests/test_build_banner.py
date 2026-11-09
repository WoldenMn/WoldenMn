"""Garde les promesses de build_banner.py.

La banniere doit rester lisible chez un moteur qui n'anime pas, ne rien charger
depuis le reseau, dire ce qu'elle dit sans compteur ni pile de langages, et
partir avec un texte alternatif qui porte les memes mots.
"""

import re
import sys
from pathlib import Path
from xml.etree import ElementTree

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import build_banner


def elements(doc, balise=None):
    """Parcourt le SVG. ElementTree prefixe les balises du namespace, d'ou le split."""
    for el in ElementTree.fromstring(doc).iter():
        if balise is None or el.tag.rsplit("}", 1)[-1] == balise:
            yield el


def titre_et_glyphes(doc):
    """Rend les <text> du titre, ceux qui portent la bascule brouillage/lettre."""
    return [t for t in elements(doc, "text") if t.get("font-size") == "44"]


def textes_visibles(doc):
    """Le texte de chaque <text> hors trame de glyphes et hors titre."""
    return [t.text or "" for t in elements(doc, "text")
            if t.get("opacity") is None and t.get("font-size") != "44"]


def depot_factice(tmp_path, alt="ancien texte, qui ne suit plus l'image"):
    """Un dossier qui ressemble assez au depot pour que main() y travaille."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "README.md").write_text(
        f'<div align="center">\n  <img src="./assets/banner.svg" alt="{alt}" width="900">\n'
        '</div>\n\nLe reste du README.\n', encoding="utf-8")
    return tmp_path


def test_svg_bien_forme():
    racine = ElementTree.fromstring(build_banner.svg())
    assert racine.tag == "{http://www.w3.org/2000/svg}svg"
    assert racine.get("viewBox") == f"0 0 {build_banner.W} {build_banner.H}"
    assert (racine.get("width"), racine.get("height")) == (str(build_banner.W), str(build_banner.H))


def test_aucune_ressource_chargee_depuis_le_reseau():
    """Chargee par <img> depuis le README, la banniere ne demande aucune
    ressource externe (le navigateur n'emet pas la requete) : tout appel sortant
    y meurt sans bruit.

    On ne cherche pas la chaine "http" betement : `xmlns` est un namespace XML,
    que personne ne va chercher sur le reseau, et `url(#scan)` pointe un degrade
    interne. Ce qui compte, c'est qu'aucun ATTRIBUT ne demande une ressource
    distante.
    """
    doc = build_banner.svg()
    assert "@import" not in doc and "<script" not in doc

    for el in elements(doc):
        for nom, valeur in el.attrib.items():
            assert "//" not in valeur, (
                f"<{el.tag} {nom}> pointe hors du fichier : {valeur}")
            if nom.rsplit("}", 1)[-1] == "href":
                assert valeur.startswith("#"), f"<{el.tag} {nom}> pointe hors du fichier : {valeur}"
    for style in elements(doc, "style"):
        assert not re.search(r"url\((?!#)", style.text or ""), "url() externe dans un <style>"


def test_titre_lisible_quand_rien_ne_s_anime():
    """Un moteur sans SMIL doit montrer WOLDENMN, jamais le brouillage fige.

    Les attributs `opacity` portent l'etat de REPOS et les <animate> les
    surchargent. Inverser les deux jeux fige le titre sur des glyphes illisibles,
    et le defaut ne se voit pas chez un moteur qui anime, c'est-a-dire partout ou
    on regarde.
    """
    lettres = set(build_banner.TITRE)
    au_repos = []
    for noeud in titre_et_glyphes(build_banner.svg()):
        if noeud.get("opacity") != "0":
            au_repos.append(noeud.text or "")

    assert au_repos, "aucun <text> visible au repos : le titre serait invisible"
    assert set(au_repos) <= lettres, (
        f"un glyphe de brouillage est visible au repos : {set(au_repos) - lettres}")
    assert "".join(au_repos) == build_banner.TITRE, (
        f"titre au repos = {''.join(au_repos)!r}, attendu {build_banner.TITRE!r}")


def test_titre_decode_une_seule_fois_puis_reste_lisible():
    """La version qui bouclait re-brouillait le titre toutes les 9 s : illisible
    40 % du temps, mesure le 2026-09-18. Chaque animation du titre joue une fois,
    puis fige une derniere valeur egale a l'etat de repos."""
    noeuds = titre_et_glyphes(build_banner.svg())
    assert noeuds
    for noeud in noeuds:
        anims = [a for a in noeud if a.tag.rsplit("}", 1)[-1] == "animate"]
        assert anims, "chaque glyphe du titre doit etre anime"
        for a in anims:
            assert a.get("repeatCount") is None, "le titre ne doit plus boucler"
            assert a.get("fill") == "freeze", "sans freeze, l'etat final se perd"
            valeurs, instants, duree = a.get("values"), a.get("keyTimes"), a.get("dur")
            assert valeurs and instants and duree, "animation incomplete"
            finale = valeurs.split(";")[-1]
            assert finale == noeud.get("opacity"), (
                f"{noeud.text!r} finit a {finale}, son repos est {noeud.get('opacity')}")
            bascule = float(instants.split(";")[-1]) * float(duree.rstrip("s"))
            assert bascule < 3.0, f"{noeud.text!r} se decode a {bascule:.2f} s"


def test_la_banniere_porte_l_accroche_et_le_terrain():
    visibles = textes_visibles(build_banner.svg())
    for attendu in (build_banner.ACCROCHE, build_banner.TERRAIN):
        assert attendu in visibles, f"texte absent de l'image : {attendu!r}"


def test_ni_compteur_ni_pile_de_langages():
    """Le profil presente un techos : plus de chiffres releves, plus de rail de
    langages, plus de lignes a points medians."""
    doc = build_banner.svg()
    for texte in textes_visibles(doc):
        assert "&#183;" not in texte and "·" not in texte, f"point median dans {texte!r}"
        assert not re.search(r"\d{2}", texte), f"compteur dans {texte!r}"
        assert "priv" not in texte.lower(), f"l'atelier ferme revient : {texte!r}"
    assert "data-source" not in doc, "une provenance de chiffres sans chiffres"


def test_accents_en_entites():
    """Le rendu ne doit rien devoir a l'encodage annonce par le serveur."""
    doc = build_banner.svg()
    assert doc.isascii(), f"caractere non ASCII : {[c for c in doc if not c.isascii()][:5]}"


def test_l_alt_du_readme_suit_la_banniere(tmp_path, monkeypatch):
    """Charge en <img>, le SVG n'expose pas son aria-label : l'alt du README est
    le seul texte qu'un lecteur d'ecran recoit. Les deux portent les memes mots."""
    monkeypatch.chdir(depot_factice(tmp_path))

    assert build_banner.main() == 0

    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    trouve_alt = re.search(r'alt="([^"]*)"', readme)
    assert trouve_alt, "aucun alt dans le README"
    alt = trouve_alt.group(1)
    assert alt == build_banner.texte_alt(), f"alt inattendu : {alt!r}"
    assert "ancien texte" not in readme, "l'ancien alt est reste"
    trouve_aria = re.search(r'aria-label="([^"]*)"',
                            (tmp_path / "assets" / "banner.svg").read_text(encoding="utf-8"))
    assert trouve_aria, "aucun aria-label dans la banniere"
    assert trouve_aria.group(1) == build_banner.entites(alt)


def test_refus_quand_le_readme_n_a_pas_la_balise_attendue(tmp_path, monkeypatch, capsys):
    """Un README dont la balise a bouge doit faire echouer le build, pas laisser
    partir une banniere neuve avec un alt qui ne la suit plus."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "assets").mkdir()
    (tmp_path / "README.md").write_text("plus aucune balise img ici\n", encoding="utf-8")

    assert build_banner.main() == 1
    assert not (tmp_path / "assets" / "banner.svg").exists(), (
        "la banniere a ete ecrite alors que son texte alternatif ne pouvait pas suivre")
    assert "ECHEC" in capsys.readouterr().err


def test_refus_quand_le_readme_est_absent(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "assets").mkdir()

    assert build_banner.main() == 1
    assert not (tmp_path / "assets" / "banner.svg").exists()
    assert "ECHEC" in capsys.readouterr().err
