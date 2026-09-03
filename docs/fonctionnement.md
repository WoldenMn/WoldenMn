# Comment ce depot fonctionne

Depot special GitHub : un depot **public** nomme exactement comme le compte
(`WoldenMn/WoldenMn`) voit son `README.md` affiche en haut de la page de profil.

## La banniere

`assets/banner.svg` n'est jamais edite a la main. Il est genere par
`build_banner.py`, qui lit les compteurs depuis l'API GitHub via `gh`.

```bash
python build_banner.py                 # interroge l'API
python build_banner.py --offline TOTAL PUBLICS LANGAGES  # valeurs explicites, pour tester
```

Si l'API est injoignable, le script **echoue et n'ecrit rien** : mieux vaut une
banniere perimee qu'une banniere fausse.

## Pourquoi SMIL et pas des animations CSS

GitHub sert les images des README a travers son proxy `camo`, qui renvoie la CSP
`default-src 'none'; img-src data:; style-src 'unsafe-inline'`. Verifie le
2026-08-22 en recuperant un SVG anime reellement servi par camo :

- les balises SMIL `<animate>` passent intactes ;
- les blocs `<style>` passent (`style-src 'unsafe-inline'`) ;
- **aucune police externe ne se charge** (`default-src 'none'`), d'ou les
  familles generiques `Consolas / monospace`.

Les attributs `opacity` portent l'etat de **repos** (titre lisible), et les
animations les surchargent tant qu'elles tournent. Un moteur qui n'anime pas
affiche donc `WOLDENMN`, jamais le brouillage fige.

## Le rafraichissement, a la demande

```powershell
.\rafraichir.ps1        # regenere et montre ce qui a bouge
.\rafraichir.ps1 -Push  # regenere, commite et publie
```

Le script s'arrete si `build_banner.py` echoue, et la banniere reste alors
intacte plutot que de porter un chiffre faux. Verifie le 2026-09-03 dans les
deux sens : compteurs a jour quand l'API repond, aucune ecriture quand `gh` est
hors d'atteinte.

### Pourquoi plus de GitHub Actions

Un workflow hebdomadaire tournait ici jusqu'au 2026-09-03. Il exigeait un secret
`PROFILE_STATS_TOKEN`, parce que le `GITHUB_TOKEN` d'Actions ne voit que ce
depot-ci et aurait compte deux depots au lieu de cinquante. Le secret n'a jamais
ete pose : le workflow a echoue a chaque passage, deux lundis de suite, en
laissant des croix rouges sur un depot dont le seul role est de bien paraitre.

Le choix retenu est d'assumer la relance manuelle plutot que de deposer un jeton
a portee large dans un depot public. L'ancien workflow reste dans
`_archive/2026-09-03_workflow-vers-script-local/` si le compromis change.

## Direction visuelle

`bento-dense` (skill `esthetiques`) : fond sombre, Consolas, rayon 10, bordure
discrete. Un seul interdit de la fiche est leve, l'animation permanente, a la
demande explicite du proprietaire.
