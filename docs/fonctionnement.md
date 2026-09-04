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

## Les deux autres assets

| Fichier | Sert a | Ou il se televerse |
|---|---|---|
| `assets/avatar.svg` | photo de profil du compte | Settings > Profile Picture > Edit > Upload a photo |
| `assets/social-preview.svg` | vignette quand on partage le lien du depot | Settings du depot > Social preview > Edit |

GitHub n'accepte que du PNG, du JPG ou du GIF a l'upload, d'ou :

```powershell
.\exporter_png.ps1
```

Il ecrit `export/avatar.png` (920x920) et `export/social-preview.png` (1280x640),
hors du depot puisque ce sont des derives. Le binaire Edge y est **cherche**, jamais
suppose : son chemin porte un numero de version qui change a chaque mise a jour.

### Le piege du rendu, deja paye

Edge rend la main **avant** d'avoir vide son tampon sur le disque. Verifier
l'existence du PNG dans la foulee est une course, et elle repond « absent » sur un
rendu parfaitement reussi : le fichier arrive une fraction de seconde plus tard.
`Wait-Fichier` attend donc que le fichier apparaisse **puis** que sa taille cesse
de bouger, avec un plafond de 20 s. Sans cette attente, le script echoue au hasard
sur des rendus corrects, et fait accuser Edge a sa place.

### Pourquoi cet avatar-la

Le choix s'est fait sur une planche de rendu **circulaire** a 180/72/40/20 px, pas
sur une grande image : GitHub affiche l'avatar a 20 px dans les listes de commits,
et les formes qui n'identifient plus rien a cette taille ont ete ecartees. Les
variantes perdantes sont dans `_archive/2026-09-03_avatars-non-retenus/`.

## Direction visuelle

`bento-dense` (skill `esthetiques`) : fond sombre, Consolas, rayon 10, bordure
discrete. Un seul interdit de la fiche est leve, l'animation permanente, a la
demande explicite du proprietaire.
