"""Genere assets/banner.svg : banniere du profil GitHub WoldenMn.

Fond sombre, Consolas, rayon 10, bordure discrete. Animation SMIL (les
animations CSS passeraient aussi). Chargee par <img> depuis le README, l'image
ne charge aucune ressource externe, quelle que soit la CSP de
raw.githubusercontent.com : c'est le mode image qui l'interdit.

La banniere ne porte aucun compteur : elle dit qui tient le compte, un techos
fan de tech, pas une pile de langages. Ses textes vivent dans les constantes
ci-dessous, et le texte alternatif du README les suit a chaque generation.

Usage :
    python build_banner.py
"""

import itertools
import re
import sys

W, H = 900, 240
CYCLE = 9.0

FOND, BORD = "#12141a", "#2f3441"
TEXTE, TEXTE_2, OK = "#e6e8ee", "#949aa8", "#3ecf8e"
MONO = "Consolas, 'Cascadia Mono', 'DejaVu Sans Mono', monospace"

TITRE = "WOLDENMN"
BROUILLAGE = ["#", "%", "&amp;", "@", "$", "/", "?", "8"]
PAS, X0, Y_TITRE = 46, 56, 108

DOSSIER = "~/woldenm"
ACCROCHE = "techos, fan de tech. je teste, je casse, je répare."
TERRAIN = "windows au quotidien, un serveur à la maison, une imprimante 3D, du stream"
ETAT = "en ligne"


def entites(texte):
    """Accents en entites numeriques : le rendu ne depend pas de l'encodage
    annonce par le serveur qui sert l'image."""
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in texte)


def texte_alt():
    """Le texte alternatif de la banniere dans le README.

    Charge en <img>, le SVG n'expose pas son aria-label : l'alt de la balise est
    le seul texte qu'un lecteur d'ecran recoit. Il porte donc les memes mots que
    l'image.
    """
    return f"WoldenMn, {ACCROCHE} {TERRAIN}."


def maj_alt_readme(chemin, alt):
    """Reecrit l'attribut alt de la banniere dans le README, et rend True si le
    fichier a change.

    Leve si la balise est introuvable ou en double : mieux vaut un echec bruyant
    qu'un README qui garde en silence un texte qui ne suit plus l'image.
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


def svg():
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{entites(texte_alt())}">
  <title>WoldenMn, techos fan de tech</title>
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
  <text x="{X0 + 16}" y="66" font-family="{MONO}" font-size="12" fill="{TEXTE_2}">{entites(DOSSIER)}</text>

  {decode()}

  <rect x="{X0}" y="130" width="{PAS * len(TITRE)}" height="1" fill="{BORD}"/>
  <text x="{X0}" y="154" font-family="{MONO}" font-size="14" fill="{TEXTE}">{entites(ACCROCHE)}</text>

  <rect x="{X0 - 14}" y="176" width="{W - 2 * (X0 - 14)}" height="1" fill="{BORD}"/>
  <text x="{X0}" y="210" font-family="{MONO}" font-size="12" fill="{TEXTE_2}">{entites(TERRAIN)}</text>

  <text x="{W - 56}" y="210" text-anchor="end" font-family="{MONO}" font-size="12" fill="{TEXTE_2}">{entites(ETAT)}</text>
  <circle cx="{W - 40}" cy="206" r="4" fill="{OK}">
    <animate attributeName="opacity" values="1;1;0.15;1;1" keyTimes="0;0.45;0.5;0.55;1" dur="2.6s" repeatCount="indefinite"/>
  </circle>
  </g>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{BORD}"/>
</svg>
'''


def main():
    try:
        readme_change = maj_alt_readme("README.md", texte_alt())
    except (RuntimeError, OSError) as e:
        print(f"ECHEC : {e}", file=sys.stderr)
        print("rien n'a ete ecrit : la banniere et son texte alternatif vont par paire.",
              file=sys.stderr)
        return 1

    with open("assets/banner.svg", "w", encoding="utf-8") as f:
        f.write(svg())
    print("assets/banner.svg : regeneree")
    if readme_change:
        print("README.md : texte alternatif de la banniere mis a jour")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
