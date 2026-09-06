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

### Le piege du rendu, paye deux fois

Edge rend la main **avant** d'avoir vide son tampon sur le disque. Verifier
l'existence du PNG dans la foulee est une course, et elle repond « absent » sur un
rendu parfaitement reussi : le fichier arrive une fraction de seconde plus tard.
Sans attente, le script echoue au hasard sur des rendus corrects, et fait accuser
Edge a sa place.

La premiere correction attendait que la **taille** cesse de bouger. Elle a tenu
trois jours. Le 2026-09-06, un test l'a refutee : sur un fichier ecrit par
morceaux, `Wait-Fichier` rendait 1 Ko sur 10. Deux lectures identiques ne prouvent
pas la fin de l'ecriture, seulement que rien n'a bouge pendant l'intervalle de
scrutation. Un PNG tronque serait passe pour bon, et personne ne l'aurait vu.

La complétude se lit desormais **dans le fichier** : signature de 8 octets en tete,
chunk `IEND` en queue. Aucun chronometre, donc rien a regler et rien qui depende de
la vitesse du disque. `Test-PngComplet` ouvre en partage lecture-ecriture, puisque
Edge tient encore le fichier.

> Lecon generale : quand une garde repose sur « ca n'a pas bouge depuis un moment »,
> c'est une heuristique deguisee en preuve. Si le format porte sa propre marque de
> fin, la lire coute moins cher et ne ment pas.

### Pourquoi cet avatar-la

Le choix s'est fait sur une planche de rendu **circulaire** a 180/72/40/20 px, pas
sur une grande image : GitHub affiche l'avatar a 20 px dans les listes de commits,
et les formes qui n'identifient plus rien a cette taille ont ete ecartees. Les
variantes perdantes sont dans `_archive/2026-09-03_avatars-non-retenus/`.

## Les tests

```bash
python -m pytest tests/
```

```powershell
powershell -NoProfile -Command "Invoke-Pester .\tests\Scripts.Tests.ps1"
```

Deux suites : 7 tests Python sur `build_banner.py`, 12 tests Pester sur les deux
scripts PowerShell. Pester 5 vit dans les modules de **Windows PowerShell 5.1** sur
ce poste, pas dans ceux de pwsh 7 — d'ou l'appel par `powershell`, sans quoi c'est
la 3.4 livree avec Windows qui repond et la syntaxe ne passe pas.

Cote Python, sept tests sur des promesses reelles plutot que sur la forme du dessin :
les compteurs rendus sur deux chiffres, le SVG bien forme, **aucun attribut qui
pointe hors du fichier** (camo sert la banniere avec `default-src 'none'`, un appel
sortant y meurt sans bruit), le titre lisible quand rien ne s'anime, et surtout le
refus d'ecrire quand l'API est muette.

Ce dernier est le seul qui compte vraiment : c'est la promesse du depot entier.
Elle n'etait tenue que par une verification a la main jusqu'au 2026-09-06.

Cote PowerShell, les tests gardent le commit scope de `rafraichir.ps1` (un `git
commit` sans pathspec publierait tout l'index sous un message qui ne le mentionne
pas, c'est arrive), le refus de publier sans `-Push`, la recherche du binaire Edge,
et la complétude du PNG : fichier vide, fichier dodu qui n'est pas une image,
fichier portant `IEND` sans signature, chunk final qui arrive en retard.

### Les tests ont ete vus echouer

Un test qui n'a jamais rougi ne prouve rien. Chaque garde a ete mutee dans une copie,
puis la suite relancee.

| Suite | Mutations injectees | Attrapees |
|---|---|---|
| `build_banner.py` | opacites de repos inversees, image distante, compteurs sans zero de tete, ecriture malgre l'echec d'API, garde-fou du zero depot retire | 5/5 |
| scripts PowerShell | commit non scope, garde `python` retiree, publication sans `-Push`, chemin Edge bidon rendu, `IEND` non verifie, signature non verifiee, attente supprimee | 7/7 |

Deux enseignements du passage, plus utiles que le score :

- Un test qui verifie **le retour** peut etre aveugle quand la version cassee rend
  la meme valeur pour une mauvaise raison. Sur un fichier vide, saine comme cassee
  rendent `0` : seule la **duree** les separe.
- La garde de taille minimale de `Test-PngComplet` est une **mutation equivalente** :
  la retirer ne change aucun comportement observable, les deux comparaisons d'octets
  la rendent redondante. Elle reste par defense en profondeur, pas par couverture.

A refaire si la suite grossit, sinon rien ne dit qu'un nouveau test mord.

## Direction visuelle

`bento-dense` (skill `esthetiques`) : fond sombre, Consolas, rayon 10, bordure
discrete. Un seul interdit de la fiche est leve, l'animation permanente, a la
demande explicite du proprietaire.
