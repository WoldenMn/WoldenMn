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

## Le rafraichissement automatique

`.github/workflows/refresh-banner.yml` relance la generation chaque lundi.

Il exige un secret `PROFILE_STATS_TOKEN` : le `GITHUB_TOKEN` par defaut d'Actions
ne voit que ce depot-ci, il compterait les seuls depots publics. Creer un PAT en
**lecture seule** (classic : `read:user` + `repo`) et le poser dans
Settings > Secrets and variables > Actions.

Sans ce secret, le workflow **echoue explicitement** au lieu de publier des
compteurs faux.

## Direction visuelle

`bento-dense` (skill `esthetiques`) : fond sombre, Consolas, rayon 10, bordure
discrete. Un seul interdit de la fiche est leve, l'animation permanente, a la
demande explicite du proprietaire.
