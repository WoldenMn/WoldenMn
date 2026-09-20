# Comment ce dépôt fonctionne

Dépôt spécial de GitHub : un dépôt **public** nommé exactement comme le compte
(`WoldenMn/WoldenMn`) voit son `README.md` affiché en haut de la page de profil.

## La bannière

`assets/banner.svg` n'est jamais édité à la main. Il est généré par
`build_banner.py`, qui relève les compteurs sur l'API GitHub via `gh`.

```bash
python build_banner.py                                   # interroge l'API
python build_banner.py --offline TOTAL PUBLICS LANGAGES  # valeurs explicites, pour tester
```

Le script **échoue et n'écrit rien** dans trois cas : l'API est injoignable, elle
renvoie zéro dépôt, ou tous les dépôts vus sont publics. Le troisième trahit un
jeton qui ne voit pas les dépôts privés, le `GITHUB_TOKEN` d'Actions par exemple :
il rendrait un compte partiel sans la moindre erreur. Mieux vaut une bannière
périmée qu'une bannière fausse.

Le fichier produit porte `data-source="api"`, ou `data-source="offline"` s'il
vient du mode explicite. Sans cette marque, une bannière tapée à la main serait
indiscernable d'un relevé, et la phrase du README invérifiable sur la pièce
elle-même.

Deux angles morts, assumés :

- une visibilité **partielle** passe : un jeton qui verrait trois dépôts privés sur
  cinquante rendrait un compte faux mais plausible ;
- le jour où tout serait public, le script refuserait d'écrire. L'échec est
  bruyant, et acceptable tant que l'atelier reste fermé.

Le rail « TS · PYTHON · RUST · DOTNET · PWSH » n'est pas un compteur : c'est la
pile revendiquée, écrite à la main et assumée comme telle. Le « 09 LANGAGES » à
côté, lui, est dérivé : le nombre de langages principaux distincts.

## Ce que le rendu permet

Une image relative du README (`./assets/banner.svg`) est réécrite par GitHub en
`/raw/`, puis redirigée vers `raw.githubusercontent.com`, qui l'envoie avec la CSP
`default-src 'none'; style-src 'unsafe-inline'; sandbox` et un
`Cache-Control: max-age=300` (mesuré le 2026-09-18).

Mais c'est la balise `<img>` qui fixe les règles. Un SVG chargé comme image ne
charge **aucune ressource externe**, quelle que soit la CSP, sauf ce qui est
intégré en URI `data:`
([MDN, « SVG as an image »](https://developer.mozilla.org/en-US/docs/Web/SVG/Guides/SVG_as_an_image)).
La CSP ne joue qu'à l'ouverture directe du fichier. Ce qui en découle :

- les animations passent, SMIL comme CSS (vérifié sous Edge 153) ; la bannière
  n'utilise que SMIL ;
- aucune police externe : Consolas en local, avec repli `monospace` ;
- après un push, la bannière peut mettre quelques minutes à changer, jusqu'à dix
  environ : `max-age=300` au CDN, puis autant dans le navigateur d'un visiteur qui
  avait déjà l'image.

Les six versions précédentes de cette page accusaient toutes le proxy `camo`,
qui ne concerne en réalité que les images en URL absolue, et lui prêtaient une
CSP qui n'est pas celle de `raw.githubusercontent.com`. Les conclusions
tenaient, l'explication non.

Les accents du texte visible sont écrits en entités numériques (`&#233;`) : le
rendu ne dépend pas de l'encodage annoncé par le serveur.

### Le titre se décode une fois

Au chargement de l'image, chaque lettre de `WOLDENMN` bascule d'un glyphe brouillé
vers le vrai caractère, en cascade, puis se fige. La première version rejouait ce
décodage toutes les 9 secondes : le titre était illisible 40 % du temps, et
entièrement brouillé 16 % du temps (mesuré le 2026-09-18). Le balayage vert et le
point clignotant gardent leur boucle.

Les attributs `opacity` portent l'état de **repos** (titre lisible), et la valeur
figée de chaque animation le retrouve. Un moteur qui n'anime pas affiche donc
`WOLDENMN`, jamais le brouillage.

Un piège pour qui voudrait le vérifier en image : Edge headless, avec
`--virtual-time-budget`, n'avance presque pas le temps d'un SVG chargé par
`<img>`. Insérer le SVG dans la page aide, mais ne suffit pas : sur douze
captures identiques, trois à quatre tombent encore à l'état de départ, titre
entièrement brouillé. Or cette image-là est exactement celle que produirait le
défaut que les tests gardent, l'inversion des opacités de repos. Une capture ne
tranche donc rien ici. Le verdict se lit dans le fichier, et c'est ce que font
les tests : valeur figée de chaque animation égale à l'opacité de repos.

## Le rafraîchissement, à la demande

```powershell
.\rafraichir.ps1        # régénère et montre ce qui a bougé
.\rafraichir.ps1 -Push  # régénère, commite et publie
```

Depuis PowerShell 7. Sous Windows PowerShell 5.1, dont la stratégie d'exécution
est souvent `Restricted`, passer par
`powershell -NoProfile -ExecutionPolicy Bypass -File .\rafraichir.ps1`.

Le script s'arrête si `build_banner.py` échoue, et la bannière reste alors
intacte. Sans `-Push`, il ne commite ni ne pousse rien. Avec, il commite **deux
chemins et deux seulement**, `assets/banner.svg` et `README.md` : un `git commit`
sans chemin publierait tout ce qui traîne dans l'index, sous un message qui ne le
mentionne pas.

Pourquoi le README part avec la bannière : son attribut `alt` porte les mêmes
compteurs, parce qu'une image chargée en `<img>` n'expose pas l'`aria-label`
interne du SVG. L'`alt` est donc le seul texte qu'un lecteur d'écran reçoit, et
`build_banner.py` le réécrit à chaque passage. Publier l'un sans l'autre
donnerait une image à jour commentée par des chiffres périmés.

### Pourquoi plus de GitHub Actions

Un workflow hebdomadaire tournait ici jusqu'au 2026-09-03. Il exigeait un secret,
parce que le `GITHUB_TOKEN` d'Actions ne voit que ce dépôt-ci. Le secret n'a
jamais été posé : le workflow a échoué à chaque passage, deux lundis de suite.

La relance manuelle l'a remplacé, par choix du propriétaire : relancer à la main
plutôt que déposer un jeton à portée large dans un dépôt public, quitte à laisser
le chiffre dériver entre deux lancements. Le 2026-09-18, la bannière affichait
50 dépôts pour 54, faute de relance depuis le 2026-09-03.

## Les deux autres assets

| Fichier | Sert à | Où il se téléverse | État |
|---|---|---|---|
| `assets/avatar.svg` | photo de profil du compte | Settings > Profile Picture > Edit > Upload a photo | pas téléversé |
| `assets/social-preview.svg` | vignette quand on partage le lien du dépôt | Settings du dépôt > Social preview > Edit | pas téléversé |

Ces deux téléversements se font à la main, dans l'interface, et n'ont pas encore
été faits : GitHub sert donc l'identicon par défaut du compte et sa carte de
partage auto-générée. Tant que c'est le cas, ces deux fichiers sont du travail
prêt, pas du travail en place.

GitHub n'accepte que du PNG, du JPG ou du GIF à l'upload, d'où :

```powershell
.\exporter_png.ps1
```

Il écrit `export/avatar.png` (920 × 920) et `export/social-preview.png`
(1280 × 640), hors du dépôt puisque ce sont des dérivés. Le binaire Edge y est
**cherché**, jamais supposé : son chemin porte un numéro de version qui change à
chaque mise à jour.

### Le piège du rendu, payé trois fois

Edge rend la main **avant** d'avoir vidé son tampon sur le disque. Vérifier
l'existence du PNG dans la foulée est une course, et elle répond « absent » sur un
rendu parfaitement réussi : le fichier arrive une fraction de seconde plus tard.
Sans attente, le script échoue au hasard sur des rendus corrects, et fait accuser
Edge à sa place.

La première correction attendait que la **taille** cesse de bouger. Elle a tenu
moins de deux jours, du 2026-09-04 au 2026-09-06. Un test l'a réfutée : sur un fichier écrit par
morceaux, `Wait-Fichier` rendait 1 Ko sur 10. Deux lectures identiques ne prouvent
pas la fin de l'écriture, seulement que rien n'a bougé pendant l'intervalle de
scrutation. Un PNG tronqué serait passé pour bon.

La complétude se lit désormais **dans le fichier** : signature de 8 octets en
tête, chunk `IEND` en queue. Aucun chronomètre, donc rien à régler et rien qui
dépende de la vitesse du disque. `Test-PngComplet` ouvre en partage
lecture-écriture, puisque Edge tient encore le fichier.

> Quand une garde repose sur « ça n'a pas bougé depuis un moment », c'est une
> heuristique déguisée en preuve. Si le format porte sa propre marque de fin, la
> lire coûte moins cher et ne ment pas.

Le troisième piège est tombé le 2026-09-20. Le script, lancé sous Windows
PowerShell 5.1, s'est arrêté sur une ligne qu'Edge avait écrite sur sa sortie
d'erreur : un refus d'accès à sa clé de mise à jour, sans rapport avec le rendu,
avec un code de sortie nul. Sous `$ErrorActionPreference = 'Stop'`, Windows
PowerShell 5.1 transforme cette ligne en erreur fatale, y compris redirigée vers
`$null`. PowerShell 7 l'ignore. Le script annonce `#Requires -Version 5.1` mais
n'avait jamais été lancé que sous 7, donc le défaut vivait dans la seule version
que personne n'essayait.

```powershell
$ErrorActionPreference = 'Stop'
& cmd.exe /c 'echo bruit 1>&2 & exit 0' 2>$null   # 5.1 : erreur.  7 : rien.
```

Deuxième défaut, découvert du même coup : le PNG était supprimé **avant** le
rendu. L'échec a donc emporté un fichier valide au passage. Le rendu va
maintenant dans un fichier provisoire, et ne remplace l'ancien qu'une fois jugé
complet. `Invoke-Externe` isole l'appel au binaire, y neutralise la préférence
d'erreur et juge sur le **code de sortie**. Deux tests Pester le tiennent.
Un troisième, qui vérifiait la restauration de la préférence, a été retiré :
la passe de mutation a montré qu'il ne mordait pas, l'affectation étant locale
à la fonction. Le code de restauration est parti avec lui.

### Pourquoi cet avatar-là

Le choix s'est fait sur une planche de rendu **circulaire** à 180, 72, 40 et
20 px, pas sur une grande image : GitHub affiche l'avatar à 20 px dans les listes
de commits, et les formes qui n'identifient plus rien à cette taille ont été
écartées.

## Les tests

```bash
python -m pytest tests/
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "Import-Module Pester -MinimumVersion 5.0.0; Invoke-Pester .\tests\Scripts.Tests.ps1"
```

14 tests Python sur `build_banner.py`, 18 tests Pester sur les deux scripts
PowerShell. Pester 5 est requis. S'il n'est installé que pour Windows PowerShell
5.1 et que la stratégie d'exécution est `Restricted`, le module ne se charge pas
sans `-ExecutionPolicy Bypass`, dont la portée se limite à ce processus.

Côté Python, les tests gardent ce que le dépôt promet plutôt que la forme du
dessin : le refus d'écrire quand l'API est muette, renvoie zéro dépôt ou ne voit
que du public ; le calcul des trois compteurs sur une sortie réaliste de `gh`, où
chaque erreur plausible donne un autre triplet ; le titre décodé une seule fois et
lisible au repos ; aucune référence qui sorte du fichier, ni en attribut ni en
`url()` de style ; les compteurs sur deux chiffres ; l'accord de « visible » ;
le texte alternatif du README porteur des mêmes chiffres que la bannière, et le
refus d'écrire quoi que ce soit si ce README ne peut pas suivre.

Côté PowerShell, `rafraichir.ps1` est **exécuté** sous des mocks de `git` et de
`python` qui enregistrent chaque appel : rien ne part sans `-Push` ; avec, un seul
commit limité à `assets/banner.svg`, puis un push simple, jamais forcé ; rien non
plus quand les compteurs n'ont pas bougé ou que `build_banner.py` échoue. Un
commit qui échoue arrête tout avant le push, et un push qui échoue lève une
erreur au lieu d'annoncer la bannière publiée. Pour
`exporter_png.ps1` : la recherche d'Edge, la complétude du PNG face à un
fichier vide, un fichier dodu qui n'est pas une image, un `IEND` sans signature et
un chunk final qui arrive en retard, et l'appel au binaire, qui doit survivre à
du bruit sur la sortie d'erreur et rendre le code de sortie.

### Les tests ont été vus échouer

```bash
python tests/mutations.py
```

Un test qui n'a jamais rougi ne prouve rien. `tests/mutations.py` casse une à une
les gardes **couvertes par la suite** dans une copie du dépôt, relance les tests,
et vérifie qu'ils rougissent. Ce que ça ne couvre pas : le corps de
`exporter_png.ps1`, en dessous de `Get-CheminEdge`, n'est pas exécuté par la
suite, qui n'en charge que les fonctions. Les gardes qui vivent là, dont le
remplacement du PNG seulement une fois le rendu complet, n'ont pas de mutation
qui les vise. Deux témoins encadrent la passe : le code sain doit rester vert, et un
test cassé exprès doit rougir. Sans le second, un outil qui ne voit rien répond
« vert » à tout. Chaque mutation nomme aussi le test censé la prendre : si c'est
un autre test qui rougit, elle compte comme un trou de la suite, pas comme une
prise.

| Suite | Mutations injectées | Attrapées |
|---|---|---|
| `build_banner.py` | publics inversés, langage absent compté, total confondu avec les publics, langages confondus avec le total, garde « tout public » retirée, garde « zéro dépôt » retirée, écriture malgré l'échec d'API, titre qui boucle à nouveau, `freeze` retiré, glyphe qui finit visible, décodage tardif, cycle ralenti, opacités de repos inversées, image distante, image relative, `url()` externe dans un style, compteur sans zéro de tête, accord de « visible » faux, texte alternatif du README laissé tel quel, garde de la balise du README retirée, provenance de la bannière retirée | 21/21 |
| scripts PowerShell | `exit 0` retiré du bloc sans `-Push`, commit sans chemin, push forcé, échec de `git commit` ignoré, échec de `git push` ignoré, garde `python` neutralisée, contrôle des compteurs inchangés retiré, échec de `build_banner.py` ignoré, chemin Edge inexistant rendu, `IEND` non vérifié, signature non vérifiée, attente supprimée, appel externe rendu sensible au bruit de stderr, code de sortie ignoré | 14/14 |

Ce que les passes successives ont appris, plus utile que le score :

- La première version des tests PowerShell cherchait du **texte** dans le script.
  Une contre-expertise a retiré le `exit 0` du bloc sans `-Push` : le script
  enchaînait alors commit et push, et la suite restait verte. Un test qui lit la
  source ne teste pas le comportement.
- Les cinq premières mutations Python ne touchaient pas au **calcul** des
  compteurs : quatre erreurs de calcul passaient. La panne décrite plus haut, un
  jeton qui ne voit que le public, n'en fait pas partie : c'est une erreur de
  données, que seule la garde « tout public » attrape.
- La première passe PowerShell a rendu 0 sur 9 : Pester ne se chargeait pas, la
  sortie était vide, et l'outil lisait ce vide comme du vert. D'où le témoin
  connu-mauvais, et d'où l'exigence qu'un motif de mutation apparaisse exactement
  une fois : une mutation posée sur la mauvaise ligne passe pour un test aveugle.
- Un test qui vérifie **le retour** peut être aveugle quand la version cassée rend
  la même valeur pour une mauvaise raison. Sur un fichier vide, saine comme cassée
  rendent `0` : seule la **durée** les sépare.
- La garde de taille minimale de `Test-PngComplet` est une **mutation
  équivalente** : la retirer ne change aucun comportement observable, les deux
  comparaisons d'octets la couvrent. Elle reste par défense en profondeur.
- Le 2026-09-20, un test tout neuf est né aveugle : il vérifiait qu'`Invoke-Externe`
  restaure `$ErrorActionPreference`, alors qu'une fonction PowerShell isole ses
  portées et que l'appelant garde la sienne de toute façon. La mutation n'a rien
  cassé, parce qu'il n'y avait rien à casser. Le test et le code de restauration
  ont été retirés ensemble. Une passe de mutation sert aussi à ça : elle montre le
  code qui ne fait rien.

À relancer dès que la suite grossit : rien d'autre ne dit qu'un nouveau test mord.

## Direction visuelle

Fond charbon `#12141a`, accent vert `#3ecf8e`, Consolas, rayon 10, bordure
discrète, grille dense. Deux animations tournent en permanence, lentes : le
balayage et le point.
