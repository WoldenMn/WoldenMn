"""Genere assets/banner.svg : banniere du profil GitHub WoldenMn.

Direction visuelle bento-dense (skill esthetiques) : fond sombre, Consolas,
rayon 10, bordure discrete. Animation SMIL uniquement -- seule technique dont
on a verifie empiriquement qu'elle survit au proxy camo de GitHub.

Les trois compteurs affiches sont DERIVES de l'API GitHub, jamais ecrits a la
main : c'est leur gardien anti-derive. Sans donnees fraiches, le script echoue
au lieu d'ecrire un chiffre perime.

Usage :
    python build_banner.py                 # interroge l'API via `gh`
    python build_banner.py --offline N V L # valeurs explicites (tests)
"""

import argparse
import itertools
import json
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
            capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
    except FileNotFoundError as e:
        raise RuntimeError("gh introuvable : impossible de rafraichir les compteurs") from e
    if out.returncode != 0:
        raise RuntimeError(f"gh a echoue : {(out.stderr or '').strip()[:200]}")
    depots = json.loads(out.stdout)
    if not depots:
        raise RuntimeError("l'API a renvoye 0 depot : refus d'ecrire des compteurs vides")
    langues = {(d.get("primaryLanguage") or {}).get("name") for d in depots}
    langues.discard(None)
    return len(depots), sum(1 for d in depots if not d["isPrivate"]), len(langues)


def anim(attr, values, key_times):
    return (f'<animate attributeName="{attr}" values="{values}" keyTimes="{key_times}" '
            f'dur="{CYCLE}s" repeatCount="indefinite" calcMode="discrete"/>')


def decode():
    """Chaque lettre bascule du glyphe brouille au vrai caractere, en cascade."""
    out = []
    for i, ch in enumerate(TITRE):
        x = X0 + i * PAS + PAS / 2
        bascule = 0.06 + i * 0.035
        kt = f"0;{bascule:.4f};0.9000;1"
        commun = (f'x="{x:.1f}" y="{Y_TITRE}" text-anchor="middle" '
                  f'font-family="{MONO}" font-size="44" font-weight="700"')
        # Les attributs opacity portent l'etat de REPOS (titre lisible) ; les
        # animations SMIL les surchargent tant qu'elles tournent. Un moteur qui
        # n'anime pas affiche donc WOLDENMN, jamais le brouillage fige.
        out.append(f'<text {commun} fill="{TEXTE_2}" opacity="0">'
                   f'{BROUILLAGE[i % len(BROUILLAGE)]}{anim("opacity", "1;0;1;1", kt)}</text>')
        out.append(f'<text {commun} fill="{TEXTE}" opacity="1">{ch}'
                   f'{anim("opacity", "0;1;0;0", kt)}</text>')
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


def svg(total, publics, langues):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="WoldenMn. {total} depots, {publics} visible publiquement, {langues} langages. TypeScript, Python, Rust, dotNET, PowerShell.">
  <title>WoldenMn &#8212; {total} depots, {publics} visible</title>
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
  {stat(X0, "DEPOTS", f"{total:02d}")}
  {stat(X0 + 150, "VISIBLES", f"{publics:02d}")}
  {stat(X0 + 300, "LANGAGES", f"{langues:02d}")}

  <text x="{W - 56}" y="196" text-anchor="end" font-family="{MONO}" font-size="10" fill="{TEXTE_2}" letter-spacing="1.6">{RAIL}</text>
  <text x="{W - 56}" y="217" text-anchor="end" font-family="{MONO}" font-size="12" fill="{TEXTE_2}">le reste est prive</text>
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
    else:
        try:
            total, publics, langues = compte_depuis_api()
        except RuntimeError as e:
            print(f"ECHEC : {e}", file=sys.stderr)
            print("banner.svg NON modifie (mieux vaut pas de mise a jour qu'un chiffre faux).",
                  file=sys.stderr)
            return 1

    with open("assets/banner.svg", "w", encoding="utf-8") as f:
        f.write(svg(total, publics, langues))
    print(f"assets/banner.svg : depots={total} publics={publics} langages={langues}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
