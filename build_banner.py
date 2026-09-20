"""Genere assets/banner.svg : banniere du profil GitHub WoldenMn.

Fond sombre, Consolas, rayon 10, bordure discrete. Animation SMIL (les
animations CSS passeraient aussi). Chargee par <img> depuis le README, l'image
ne charge aucune ressource externe, quelle que soit la CSP de
raw.githubusercontent.com : c'est le mode image qui l'interdit.

Les trois compteurs affiches sont DERIVES de l'API GitHub, jamais ecrits a la
main. Sans donnees fraiches et plausibles, le script echoue au lieu d'ecrire un
chiffre faux.

Usage :
    python build_banner.py                 # interroge l'API via `gh`
    python build_banner.py --offline N V L # valeurs explicites (tests)
"""

import argparse
import itertools
import json
import re
import subprocess
import sys

W, H = 900, 240
CYCLE = 9.0

FOND, BORD = "#12141a", "#2f3441"
TEXTE, TEXTE_2, OK = "#e6e8ee", "#949aa8", "#3ecf8e"
MONO = "Consolas, 'Cascadia Mono', 'DejaVu Sans Mono', monospace"

TITRE = "WOLDENMN"
BROUILLAGE = ["#", "%", "&amp;", "@", "$", "/", "?", "8"]
PAS, X0, Y_TITRE = 46, 56, 108
TAGLINE = "outils qui tournent sur une seule machine, correctement"
RAIL = "TS &#183; PYTHON &#183; RUST &#183; DOTNET &#183; PWSH"


def compte_depuis_api():
    """Renvoie (total, publics, langues) ou leve RuntimeError."""
    champs = "name,isPrivate,primaryLanguage"
    try:
        out = subprocess.run(
            ["gh", "repo", "list", "WoldenMn", "--limit", "500", "--json", champs],
            capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
        )
    except FileNotFoundError as e:
        raise RuntimeError("gh introuvable : impossible de rafraichir les compteurs") from e
    if out.returncode != 0:
        raise RuntimeError(f"gh a echoue : {(out.stderr or '').strip()[:200]}")
    depots = json.loads(out.stdout)
    if not depots:
        raise RuntimeError("l'API a renvoye 0 depot : refus d'ecrire des compteurs vides")
    publics = sum(1 for d in depots if not d["isPrivate"])
    # Un jeton qui ne voit que le public (le GITHUB_TOKEN d'Actions, par
    # exemple) rendrait un compte partiel sans la moindre erreur. Tant que la
    # plupart des depots restent prives, « tout est public » veut dire « le
    # jeton ne voit pas le reste ».
    if publics == len(depots):
        raise RuntimeError(f"les {len(depots)} depots vus sont tous publics : le jeton ne voit "
                           "sans doute pas les prives, refus d'ecrire un compte partiel")
    langues = {(d.get("primaryLanguage") or {}).get("name") for d in depots}
    langues.discard(None)
    return len(depots), publics, len(langues)


def accord_visible(publics):
    return "visible" if publics <= 1 else "visibles"


def phrase_compteurs(total, publics, langues, entites=False):
    """Les trois compteurs en une phrase.

    `entites=True` pour le SVG, dont le rendu ne doit rien devoir a l'encodage
    annonce par le serveur ; `False` pour le README, qui est lu en UTF-8.
    """
    depots = "d&#233;p&#244;ts" if entites else "dépôts"
    return (f"{total} {depots}, dont {publics} {accord_visible(publics)} publiquement, "
            f"{langues} langages")


def texte_alt(total, publics, langues):
    """Le texte alternatif de la banniere dans le README.

    Il porte les chiffres parce qu'il est le SEUL texte qu'un lecteur d'ecran
    recoit : charge en <img>, le SVG n'expose pas son aria-label interne, et
    l'alt de la balise l'emporte. Un alt qui annonce des compteurs sans les
    donner prive ce lecteur de ce que le depot presente comme son coeur.

    Le rail est nomme comme ce qu'il est, une pile revendiquee, pour ne pas le
    faire passer pour un releve de l'API.
    """
    return (f"WoldenMn. Bannière : {phrase_compteurs(total, publics, langues)}, "
            "relevés sur l'API GitHub. Le reste est privé. "
            "Pile revendiquée : TypeScript, Python, Rust, .NET, PowerShell.")


def maj_alt_readme(chemin, alt):
    """Reecrit l'attribut alt de la banniere dans le README, et rend True si le
    fichier a change.

    Leve si la balise est introuvable ou en double : mieux vaut un echec bruyant
    qu'un README qui garde en silence des chiffres perimes.
    """
    with open(chemin, encoding="utf-8") as f:
        avant = f.read()

    motif = re.compile(r'(<img src="\./assets/banner\.svg" alt=")([^"]*)(")')
    trouves = motif.findall(avant)
    if len(trouves) != 1:
        raise RuntimeError(f"{chemin} : {len(trouves)} balise(s) de banniere trouvee(s), il en faut 1")

    apres = motif.sub(lambda m: m.group(1) + alt + m.group(3), avant)
    if apres == avant:
        return False
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(apres)
    return True


def anim_une_fois(attr, values, key_times):
    """Joue une seule fois puis fige la derniere valeur."""
    return (f'<animate attributeName="{attr}" values="{values}" keyTimes="{key_times}" '
            f'dur="{CYCLE}s" calcMode="discrete" fill="freeze"/>')


def decode():
    """Chaque lettre bascule du glyphe brouille au vrai caractere, en cascade,
    une seule fois au chargement de l'image. La version qui bouclait laissait
    le titre illisible 40 % du temps."""
    out = []
    for i, ch in enumerate(TITRE):
        x = X0 + i * PAS + PAS / 2
        bascule = 0.06 + i * 0.035
        kt = f"0;{bascule:.4f}"
        commun = (f'x="{x:.1f}" y="{Y_TITRE}" text-anchor="middle" '
                  f'font-family="{MONO}" font-size="44" font-weight="700"')
        # Les attributs opacity portent l'etat de REPOS (titre lisible), et la
        # derniere valeur figee de chaque animation le retrouve. Un moteur qui
        # n'anime pas affiche donc WOLDENMN, jamais le brouillage fige.
        out.append(f'<text {commun} fill="{TEXTE_2}" opacity="0">'
                   f'{BROUILLAGE[i % len(BROUILLAGE)]}{anim_une_fois("opacity", "1;0", kt)}</text>')
        out.append(f'<text {commun} fill="{TEXTE}" opacity="1">{ch}'
                   f'{anim_une_fois("opacity", "0;1", kt)}</text>')
    return "\n  ".join(out)


def champ_glyphes():
    """Trame de glyphes tres faible : presence, pas lisibilite."""
    glyphes = itertools.cycle(["0", "1", "#", "/", "%", "$", "&amp;", "@", "8", "?", "+", "=", "-"])
    out = []
    for r in range(6):
        for c in range(26):
            x, y = 540 + c * 13, 44 + r * 15
            if x > W - 30:
                continue
            out.append(f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="11" '
                       f'fill="{TEXTE_2}" opacity="0.07">{next(glyphes)}</text>')
    return "\n  ".join(out)


def stat(x, label, valeur):
    return (f'<text x="{x}" y="196" font-family="{MONO}" font-size="10" '
            f'fill="{TEXTE_2}" letter-spacing="1.6">{label}</text>\n  '
            f'<text x="{x}" y="217" font-family="{MONO}" font-size="19" '
            f'font-weight="700" fill="{TEXTE}">{valeur}</text>')


def svg(total, publics, langues, source="api"):
    # Accents en entites numeriques : le rendu ne depend plus de l'encodage
    # annonce par le serveur qui sert l'image.
    #
    # data-source dit d'ou viennent les chiffres. Sans lui, un fichier produit
    # par --offline, donc tape a la main, est indiscernable d'un releve : la
    # promesse du README serait invérifiable sur l'artefact lui-meme.
    visibles = accord_visible(publics)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" data-source="{source}" aria-label="WoldenMn. {phrase_compteurs(total, publics, langues, entites=True)}. TypeScript, Python, Rust, .NET, PowerShell.">
  <title>WoldenMn &#8212; {total} d&#233;p&#244;ts, {publics} {visibles}</title>
  <defs>
    <linearGradient id="scan" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{OK}" stop-opacity="0"/>
      <stop offset="50%" stop-color="{OK}" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="{OK}" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="carte"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="10"/></clipPath>
  </defs>

  <rect width="{W}" height="{H}" rx="10" fill="{FOND}"/>
  <g clip-path="url(#carte)">
  {champ_glyphes()}

  <rect x="-200" y="1" width="200" height="{H - 2}" fill="url(#scan)">
    <animate attributeName="x" values="-200;{W}" dur="{CYCLE}s" repeatCount="indefinite"/>
  </rect>

  <rect x="{X0}" y="52" width="3" height="18" fill="{OK}"/>
  <text x="{X0 + 16}" y="66" font-family="{MONO}" font-size="11" fill="{TEXTE_2}" letter-spacing="3">SIGNAL ACQUIS</text>

  {decode()}

  <rect x="{X0}" y="130" width="{PAS * len(TITRE)}" height="1" fill="{BORD}"/>
  <text x="{X0}" y="152" font-family="{MONO}" font-size="13" fill="{TEXTE_2}">{TAGLINE}</text>

  <rect x="{X0 - 14}" y="176" width="{W - 2 * (X0 - 14)}" height="1" fill="{BORD}"/>
  {stat(X0, "D&#201;P&#212;TS", f"{total:02d}")}
  {stat(X0 + 150, "VISIBLES", f"{publics:02d}")}
  {stat(X0 + 300, "LANGAGES", f"{langues:02d}")}

  <text x="{W - 56}" y="196" text-anchor="end" font-family="{MONO}" font-size="10" fill="{TEXTE_2}" letter-spacing="1.6">{RAIL}</text>
  <text x="{W - 56}" y="217" text-anchor="end" font-family="{MONO}" font-size="12" fill="{TEXTE_2}">le reste est priv&#233;</text>
  <circle cx="{W - 40}" cy="212" r="4" fill="{OK}">
    <animate attributeName="opacity" values="1;1;0.15;1;1" keyTimes="0;0.45;0.5;0.55;1" dur="2.6s" repeatCount="indefinite"/>
  </circle>
  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{BORD}"/>
</svg>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", nargs=3, type=int, metavar=("TOTAL", "PUBLICS", "LANGAGES"))
    args = ap.parse_args()

    if args.offline:
        total, publics, langues = args.offline
        source = "offline"
    else:
        try:
            total, publics, langues = compte_depuis_api()
        except RuntimeError as e:
            print(f"ECHEC : {e}", file=sys.stderr)
            print("banner.svg NON modifie (mieux vaut pas de mise a jour qu'un chiffre faux).",
                  file=sys.stderr)
            return 1
        source = "api"

    # Le texte alternatif du README porte les memes chiffres : charge en <img>,
    # le SVG n'expose pas son aria-label, et l'alt est tout ce qu'un lecteur
    # d'ecran recoit. Le laisser a la main, c'est le laisser derailler.
    #
    # Le README passe en premier : il est le seul des deux a pouvoir refuser.
    # S'il refuse apres coup, la banniere serait deja a jour avec un alt perime,
    # c'est-a-dire le defaut qu'on corrige.
    try:
        readme_change = maj_alt_readme("README.md", texte_alt(total, publics, langues))
    except (RuntimeError, OSError) as e:
        print(f"ECHEC : {e}", file=sys.stderr)
        print("rien n'a ete ecrit : la banniere et son texte alternatif vont par paire.",
              file=sys.stderr)
        return 1

    with open("assets/banner.svg", "w", encoding="utf-8") as f:
        f.write(svg(total, publics, langues, source))
    print(f"assets/banner.svg : depots={total} publics={publics} langages={langues} source={source}")
    if readme_change:
        print("README.md : texte alternatif de la banniere mis a jour")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
