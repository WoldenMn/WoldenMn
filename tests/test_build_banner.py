"""Garde les promesses de build_banner.py.

Le coeur de ce depot n'est pas de dessiner joli : c'est que le script ecrive
des compteurs releves sur l'API, ou n'ecrive rien. La banniere peut alors rester
perimee, et un jeton a visibilite partielle passe (voir docs/fonctionnement.md).
Et que la banniere reste lisible chez un moteur qui n'anime pas. Ces deux
promesses etaient tenues a la main jusqu'ici.
"""

import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest

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


def test_compteurs_rendus_sur_deux_chiffres():
    doc = build_banner.svg(50, 2, 9)
    for attendu in (">50<", ">02<", ">09<"):
        assert attendu in doc, f"compteur absent : {attendu}"


def test_svg_bien_forme():
    ElementTree.fromstring(build_banner.svg(50, 2, 9))


def test_aucune_ressource_chargee_depuis_le_reseau():
    """Chargee par <img> depuis le README, la banniere ne demande aucune
    ressource externe (le navigateur n'emet pas la requete) : tout appel sortant
    y meurt sans bruit.

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
    for noeud in titre_et_glyphes(build_banner.svg(50, 2, 9)):
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
    noeuds = titre_et_glyphes(build_banner.svg(50, 2, 9))
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
            # Le decodage doit se voir a l'arrivee : un titre qui ne se revele
            # qu'au bout de 9 s est illisible pour qui passe vite.
            bascule = float(instants.split(";")[-1]) * float(duree.rstrip("s"))
            assert bascule < 3.0, f"{noeud.text!r} se decode a {bascule:.2f} s"


def test_accord_de_visible():
    assert "1 visible " in build_banner.svg(50, 1, 9)
    assert "2 visibles " in build_banner.svg(50, 2, 9)


class SortieGh:
    returncode = 0
    stderr = ""

    def __init__(self, depots):
        self.stdout = json.dumps(depots)


def test_compteurs_calcules_sur_une_sortie_realiste(monkeypatch):
    """La forme reelle de gh : un depot sans langage porte primaryLanguage null.

    Les valeurs attendues sont toutes distinctes (4, 1, 2) : inverser prives et
    publics, compter le langage absent, confondre total et publics, ou compter
    les langages avec leurs doublons donnent chacun un autre triplet.
    """
    depots = [
        {"name": "a", "isPrivate": True, "primaryLanguage": {"name": "Rust"}},
        {"name": "b", "isPrivate": True, "primaryLanguage": {"name": "Rust"}},
        {"name": "c", "isPrivate": True, "primaryLanguage": {"name": "TypeScript"}},
        {"name": "d", "isPrivate": False, "primaryLanguage": None},
    ]
    monkeypatch.setattr(build_banner.subprocess, "run", lambda *_a, **_k: SortieGh(depots))
    assert build_banner.compte_depuis_api() == (4, 1, 2)


def test_refus_quand_tous_les_depots_vus_sont_publics(monkeypatch):
    """Un jeton qui ne voit que le public rendrait un compte partiel sans erreur."""
    depots = [
        {"name": "a", "isPrivate": False, "primaryLanguage": None},
        {"name": "b", "isPrivate": False, "primaryLanguage": {"name": "Python"}},
    ]
    monkeypatch.setattr(build_banner.subprocess, "run", lambda *_a, **_k: SortieGh(depots))
    with pytest.raises(RuntimeError, match="tous publics"):
        build_banner.compte_depuis_api()


def test_refus_d_ecrire_quand_l_api_est_muette(tmp_path, monkeypatch, capsys):
    """API injoignable : code de sortie non nul, et surtout aucune ecriture."""
    def api_muette():
        raise RuntimeError("gh introuvable")

    monkeypatch.setattr(build_banner, "compte_depuis_api", api_muette)
    monkeypatch.setattr(sys, "argv", ["build_banner.py"])
    # Un depot complet, README compris : sans lui, le build echouerait sur le
    # README absent et ce test passerait pour une autre raison que la sienne.
    monkeypatch.chdir(depot_factice(tmp_path))

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
    # Le message exact compte : sans cette garde, la liste vide tombe sur celle du
    # « tout public » (0 == 0) et le diagnostic affiche une mauvaise cause.
    with pytest.raises(RuntimeError, match="compteurs vides"):
        build_banner.compte_depuis_api()


def depot_factice(tmp_path, alt="ancien texte, avec de vieux chiffres"):
    """Un dossier qui ressemble assez au depot pour que main() y travaille."""
    (tmp_path / "assets").mkdir()
    (tmp_path / "README.md").write_text(
        f'<div align="center">\n  <img src="./assets/banner.svg" alt="{alt}" width="900">\n'
        '</div>\n\nLe reste du README.\n', encoding="utf-8")
    return tmp_path


def test_mode_offline_ecrit_les_valeurs_donnees(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["build_banner.py", "--offline", "7", "3", "1"])
    monkeypatch.chdir(depot_factice(tmp_path))

    assert build_banner.main() == 0
    ecrit = (tmp_path / "assets" / "banner.svg").read_text(encoding="utf-8")
    assert ">07<" in ecrit and ">03<" in ecrit and ">01<" in ecrit


def test_l_alt_du_readme_porte_les_memes_chiffres_que_la_banniere(tmp_path, monkeypatch):
    """Charge en <img>, le SVG n'expose pas son aria-label : l'alt du README est
    le seul texte qu'un lecteur d'ecran recoit. Un alt fige devient faux des la
    premiere relance, et personne ne le voit."""
    monkeypatch.setattr(sys, "argv", ["build_banner.py", "--offline", "54", "2", "9"])
    monkeypatch.chdir(depot_factice(tmp_path))

    assert build_banner.main() == 0

    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    alt = re.search(r'alt="([^"]*)"', readme).group(1)
    assert "54" in alt and "2" in alt and "9" in alt, f"alt sans les compteurs : {alt!r}"
    assert "ancien texte" not in readme, "l'ancien alt est reste"
    # Les memes chiffres des deux cotes : c'est la promesse, pas la presence.
    aria = re.search(r'aria-label="([^"]*)"',
                     (tmp_path / "assets" / "banner.svg").read_text(encoding="utf-8")).group(1)
    for nombre in ("54", "2", "9"):
        assert nombre in aria and nombre in alt


def test_refus_quand_le_readme_n_a_pas_la_balise_attendue(tmp_path, monkeypatch, capsys):
    """Un README dont la balise a bouge doit faire echouer le build, pas laisser
    partir une banniere neuve avec un alt perime."""
    monkeypatch.setattr(sys, "argv", ["build_banner.py", "--offline", "54", "2", "9"])
    monkeypatch.chdir(tmp_path)
    (tmp_path / "assets").mkdir()
    (tmp_path / "README.md").write_text("plus aucune balise img ici\n", encoding="utf-8")

    assert build_banner.main() == 1
    assert not (tmp_path / "assets" / "banner.svg").exists(), (
        "la banniere a ete ecrite alors que son texte alternatif ne pouvait pas suivre")
    assert "ECHEC" in capsys.readouterr().err


def test_la_banniere_dit_d_ou_viennent_ses_chiffres():
    """Sans cette marque, un fichier produit par --offline, donc tape a la main,
    est indiscernable d'un releve sur l'API."""
    assert 'data-source="api"' in build_banner.svg(50, 2, 9)
    assert 'data-source="offline"' in build_banner.svg(50, 2, 9, "offline")
