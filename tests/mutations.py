"""Passe de mutation : chaque garde du depot est cassee a son tour, dans une
copie, et le test qui la protege doit rougir. Le depot n'est jamais touche.

Deux temoins encadrent chaque suite. Le code sain doit rester vert ; un test
casse expres doit rougir. Sans le second, un outil qui ne voit rien (Pester qui
ne se charge pas, par exemple) repond « vert » a tout.

Chaque mutation nomme le test cense la prendre. Une mutation qui fait rougir un
AUTRE test (un import casse fait tout rougir) n'est pas comptee comme attrapee :
elle signale une mutation mal posee ou un test qui ne garde pas ce qu'il dit.

Usage :
    python tests/mutations.py

Code de sortie 0 seulement si les temoins tiennent et si chaque mutation est
prise par son test.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEPOT = Path(__file__).resolve().parents[1]
FICHIERS = ["build_banner.py", "rafraichir.ps1", "exporter_png.ps1",
            "tests/test_build_banner.py", "tests/Scripts.Tests.ps1"]

CALCUL = "test_compteurs_calcules_sur_une_sortie_realiste"
TITRE = "test_titre_decode_une_seule_fois_puis_reste_lisible"
RESEAU = "test_aucune_ressource_chargee_depuis_le_reseau"

# (libelle, fichier, avant, apres, test attendu). Le motif « avant » doit
# apparaitre exactement une fois : sinon la mutation tombe sur une autre ligne.
PYTHON = [
    ("publics inverses", "build_banner.py",
     'publics = sum(1 for d in depots if not d["isPrivate"])', 'publics = sum(1 for d in depots if d["isPrivate"])', CALCUL),
    ("langage absent compte", "build_banner.py", "    langues.discard(None)\n", "", CALCUL),
    ("total = publics", "build_banner.py",
     "return len(depots), publics, len(langues)", "return publics, publics, len(langues)", CALCUL),
    ("langues = total", "build_banner.py",
     "return len(depots), publics, len(langues)", "return len(depots), publics, len(depots)", CALCUL),
    ("garde tout-public retiree", "build_banner.py", "if publics == len(depots):", "if False:",
     "test_refus_quand_tous_les_depots_vus_sont_publics"),
    ("garde zero depot retiree", "build_banner.py", "    if not depots:", "    if False:",
     "test_refus_de_compter_zero_depot"),
    ("ecrit malgre l'echec d'API", "build_banner.py",
     "            return 1\n", "            total, publics, langues = 0, 0, 0\n",
     "test_refus_d_ecrire_quand_l_api_est_muette"),
    ("titre qui boucle a nouveau", "build_banner.py",
     'calcMode="discrete" fill="freeze"', 'calcMode="discrete" fill="freeze" repeatCount="indefinite"', TITRE),
    ("freeze retire", "build_banner.py", 'calcMode="discrete" fill="freeze"', 'calcMode="discrete"', TITRE),
    ("glyphe qui finit visible", "build_banner.py",
     'anim_une_fois("opacity", "1;0", kt)', 'anim_une_fois("opacity", "0;1", kt)', TITRE),
    ("decodage tardif", "build_banner.py", "bascule = 0.06 + i * 0.035", "bascule = 0.90 + i * 0.012", TITRE),
    ("cycle ralenti", "build_banner.py", "CYCLE = 9.0", "CYCLE = 30.0", TITRE),
    ("opacites de repos inversees", "build_banner.py",
     'fill="{TEXTE_2}" opacity="0">', 'fill="{TEXTE_2}" opacity="1">', "test_titre_lisible_quand_rien_ne_s_anime"),
    ("image distante", "build_banner.py", "<defs>", '<defs><image href="https://exemple.test/f.png"/>', RESEAU),
    ("image relative", "build_banner.py", "<defs>", '<defs><image href="assets/autre.png"/>', RESEAU),
    ("url() externe dans un style", "build_banner.py", "<defs>",
     "<defs><style>@font-face{{font-family:x;src:url(police.woff)}}</style>", RESEAU),
    ("compteur sans zero de tete", "build_banner.py", 'f"{publics:02d}"', 'f"{publics:d}"',
     "test_compteurs_rendus_sur_deux_chiffres"),
    ("accord de visible faux", "build_banner.py", "if publics <= 1 else", "if publics < 1 else", "test_accord_de_visible"),
    ("alt du README laisse tel quel", "build_banner.py",
     'readme_change = maj_alt_readme("README.md", texte_alt(total, publics, langues))',
     "readme_change = False",
     "test_l_alt_du_readme_porte_les_memes_chiffres_que_la_banniere"),
    ("garde de la balise du README retiree", "build_banner.py",
     "if len(trouves) != 1:", "if False:",
     "test_refus_quand_le_readme_n_a_pas_la_balise_attendue"),
    ("provenance de la banniere retiree", "build_banner.py",
     ' data-source="{source}"', "",
     "test_la_banniere_dit_d_ou_viennent_ses_chiffres"),
]

PESTER = [
    ("exit 0 retire du bloc sans -Push", "rafraichir.ps1",
     'Write-Host "Les compteurs ont bouge. Relance avec -Push pour commiter et publier."\n    exit 0',
     'Write-Host "Les compteurs ont bouge. Relance avec -Push pour commiter et publier."',
     "sans -Push, ne commite ni ne pousse rien"),
    ("commit non scope", "rafraichir.ps1",
     'git commit -m "chore(banner): refresh derived counters" -- @derives',
     'git commit -m "chore(banner): refresh derived counters"',
     "avec -Push, un seul commit, scope aux deux fichiers derives, puis un push"),
    ("push force", "rafraichir.ps1", "git push\n", "git push --force\n",
     "avec -Push, un seul commit, scope aux deux fichiers derives, puis un push"),
    ("echec de git commit ignore", "rafraichir.ps1",
     'throw "git commit a echoue (code $LASTEXITCODE)."', 'Write-Warning "git commit a echoue (code $LASTEXITCODE)."',
     "leve et ne pousse rien quand git commit echoue"),
    ("echec de git push ignore", "rafraichir.ps1",
     'throw "git push a echoue (code $LASTEXITCODE)."', 'Write-Warning "git push a echoue (code $LASTEXITCODE)."',
     "leve quand git push echoue, au lieu d'annoncer la banniere publiee"),
    ("garde python neutralisee", "rafraichir.ps1",
     'throw "python introuvable dans le PATH : impossible de regenerer la banniere."',
     'Write-Warning "python introuvable dans le PATH : impossible de regenerer la banniere."',
     "leve si python est introuvable, sans rien lancer"),
    ("controle des compteurs inchanges retire", "rafraichir.ps1",
     "if ([string]::IsNullOrWhiteSpace($modifie)) {", "if ($false) {",
     "ne publie rien quand les compteurs n'ont pas bouge"),
    ("echec de build_banner ignore", "rafraichir.ps1",
     'if ($LASTEXITCODE -ne 0) {\n    throw "build_banner.py', 'if ($false) {\n    throw "build_banner.py',
     "ne publie rien quand build_banner.py echoue"),
    ("Edge : chemin inexistant rendu", "exporter_png.ps1",
     "foreach ($c in $candidats) { if (Test-Path -LiteralPath $c -PathType Leaf) { return $c } }",
     "return $candidats[0]", "leve plutot que de rendre un chemin qui n'existe pas"),
    ("IEND non verifie", "exporter_png.ps1",
     "return -not @(Compare-Object $tampon $FIN_IEND -SyncWindow 0).Count", "return $true",
     "attend le chunk final, pas la premiere taille venue"),
    ("signature non verifiee", "exporter_png.ps1",
     "if (@(Compare-Object $tampon $SIGNATURE -SyncWindow 0).Count) { return $false }", "",
     "refuse un fichier qui finit par IEND sans commencer par la signature"),
    ("attente supprimee", "exporter_png.ps1", "(Test-PngComplet $Chemin)", "$true",
     "refuse un fichier bien dodu qui n'est pas un PNG"),
    ("appel externe rendu sensible au stderr", "exporter_png.ps1",
     "    $ErrorActionPreference = 'Continue'\n", "    $ErrorActionPreference = 'Stop'\n",
     "ne leve pas quand le binaire ecrit sur stderr et sort a zero"),
    ("code de sortie ignore", "exporter_png.ps1", "return $LASTEXITCODE", "return 0",
     "rend le code de sortie du binaire plutot que de l'ignorer"),
    ("README retire du commit", "rafraichir.ps1",
     "$derives = @('assets/banner.svg', 'README.md')", "$derives = @('assets/banner.svg')",
     "avec -Push, un seul commit, scope aux deux fichiers derives, puis un push"),
    ("splatting retire du commit", "rafraichir.ps1",
     'git commit -m "chore(banner): refresh derived counters" -- @derives',
     'git commit -m "chore(banner): refresh derived counters" -- $derives',
     "avec -Push, un seul commit, scope aux deux fichiers derives, puis un push"),
]

TEMOIN_PYTHON = ("tests/test_build_banner.py", "ElementTree.fromstring(build_banner.svg(50, 2, 9))",
                 "assert False", "test_svg_bien_forme")
TEMOIN_PESTER = ("tests/Scripts.Tests.ps1", "Get-CheminEdge | Should -Exist", "$false | Should -BeTrue",
                 "trouve un binaire reel sur ce poste")


class InstrumentMuet(RuntimeError):
    pass


def lire(chemin):
    return chemin.read_text(encoding="utf-8").replace("\r\n", "\n")


def ecrire(chemin, texte):
    chemin.write_text(texte, encoding="utf-8", newline="\n")


def copie():
    d = Path(tempfile.mkdtemp(prefix="mutations-profil-"))
    for f in FICHIERS:
        (d / f).parent.mkdir(parents=True, exist_ok=True)
        ecrire(d / f, lire(DEPOT / f))
    (d / "assets").mkdir(exist_ok=True)
    return d


def echecs_python(d):
    """Rend l'ensemble des tests en echec, ou leve si pytest n'a rien rapporte."""
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/test_build_banner.py", "-q", "-rf", "-p", "no:cacheprovider"],
                       cwd=d, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, check=False)
    if "passed" not in r.stdout and "failed" not in r.stdout:
        raise InstrumentMuet(f"pytest n'a rien rapporte (code {r.returncode}) : {r.stderr.strip()[:300]}")
    return {l.split("::", 1)[1].split(" ", 1)[0] for l in r.stdout.splitlines() if l.startswith("FAILED ") and "::" in l}


def echecs_pester(d):
    # Pester 5 peut n'exister que sous Windows PowerShell 5.1, dont la strategie
    # est souvent Restricted : sans Bypass (portee : ce processus), le module ne
    # se charge pas et la sortie est vide.
    fichier = d / "tests" / "Scripts.Tests.ps1"
    cmd = (f"Import-Module Pester -MinimumVersion 5.0.0 -ErrorAction Stop; "
           f"$x = Invoke-Pester -Path '{fichier}' -PassThru -Output None; "
           f"'PASSES=' + $x.PassedCount; 'ECHECS=' + $x.FailedCount; "
           f"$x.Failed | ForEach-Object {{ 'ECHOUE=' + $_.Name }}")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    compte, noms = {}, set()
    for ligne in r.stdout.splitlines():
        cle, _, valeur = ligne.strip().partition("=")
        if cle in ("PASSES", "ECHECS") and valeur.isdigit():
            compte[cle] = int(valeur)
        elif cle == "ECHOUE":
            noms.add(valeur)
    if len(compte) != 2 or compte["PASSES"] + compte["ECHECS"] == 0:
        raise InstrumentMuet(f"Pester n'a rien rapporte (code {r.returncode}) : {r.stderr.strip()[:300]}")
    if compte["ECHECS"] != len(noms):
        raise InstrumentMuet(f"Pester annonce {compte['ECHECS']} echec(s) mais en nomme {len(noms)}")
    return noms


def muter(d, fichier, avant, apres):
    cible = d / fichier
    sain = lire(cible)
    if sain.count(avant) != 1:
        raise InstrumentMuet(f"motif trouve {sain.count(avant)} fois dans {fichier}, il en faut exactement 1 : {avant[:60]!r}")
    ecrire(cible, sain.replace(avant, apres))
    return cible, sain


def controle_des_motifs(d, mutations, temoin):
    """Verifie d'un coup que chaque motif vise une occurrence et une seule.

    Sans ce controle, un motif devenu obsolete n'apparait qu'au moment ou son
    tour vient, apres avoir deja depense plusieurs minutes de suite Pester.
    """
    # Le temoin porte (fichier, motif, remplacement, test) ; une mutation porte
    # un libelle en plus, devant.
    a_verifier = [("temoin", temoin[0], temoin[1])]
    a_verifier += [(libelle, fichier, avant) for libelle, fichier, avant, _, _ in mutations]

    morts = []
    for libelle, fichier, avant in a_verifier:
        vus = lire(d / fichier).count(avant)
        if vus != 1:
            morts.append(f"{libelle} : {vus} occurrence(s) dans {fichier}")
    if morts:
        raise InstrumentMuet("motifs qui ne visent plus une occurrence unique :\n    "
                             + "\n    ".join(morts))


def passe(nom, mutations, echecs, temoin):
    print(f"=== {nom} ===")
    d = copie()
    controle_des_motifs(d, mutations, temoin)
    try:
        if echecs(d):
            print("  temoin connu-bon ROUGE : la suite echoue deja sur le code sain")
            return False
        *casse, attendu = temoin
        cible, sain = muter(d, *casse)
        try:
            if attendu not in echecs(d):
                print("  temoin connu-mauvais non vu : l'instrument ne voit rien")
                return False
        finally:
            ecrire(cible, sain)
        print("  temoins : code sain vert, test casse expres rouge")
        prises = 0
        for libelle, fichier, avant, apres, test in mutations:
            cible, sain = muter(d, fichier, avant, apres)
            try:
                rouges = echecs(d)
            finally:
                ecrire(cible, sain)
            if test in rouges:
                prises += 1
                verdict = "prise"
            elif rouges:
                verdict = f"ROUGIE PAR UN AUTRE TEST : {', '.join(sorted(rouges))[:80]}"
            else:
                verdict = "AVEUGLE"
            print(f"  {libelle:42} {verdict}")
        print(f"  -> {prises}/{len(mutations)}")
        return prises == len(mutations)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    try:
        ok_py = passe("pytest", PYTHON, echecs_python, TEMOIN_PYTHON)
        ok_ps = passe("Pester", PESTER, echecs_pester, TEMOIN_PESTER)
    except InstrumentMuet as e:
        print(f"ECHEC DE L'INSTRUMENT : {e}", file=sys.stderr)
        return 2
    return 0 if ok_py and ok_ps else 1


if __name__ == "__main__":
    raise SystemExit(main())
