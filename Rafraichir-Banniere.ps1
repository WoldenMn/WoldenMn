#Requires -Version 5.1
<#
.SYNOPSIS
    Regenere la banniere et son texte alternatif, puis les commite et les pousse s'ils ont change.
.DESCRIPTION
    build_banner.py ecrit assets/banner.svg a partir des textes ranges en tete du
    script, et reecrit l'attribut alt de la banniere dans le README. Ce script le
    lance, montre ce qui a change, et ne commite rien sans -Push. Si
    build_banner.py echoue, il s'arrete avec lui et la banniere reste intacte.
.PARAMETER Push
    Commite et pousse les deux fichiers generes. Sans ce commutateur, le script
    se contente de regenerer et d'afficher ce qui a change.
.EXAMPLE
    .\Rafraichir-Banniere.ps1
    .\Rafraichir-Banniere.ps1 -Push
#>
[CmdletBinding()]
param([switch]$Push)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python introuvable dans le PATH : impossible de regenerer la banniere."
}

python build_banner.py
if ($LASTEXITCODE -ne 0) {
    throw "build_banner.py a echoue (code $LASTEXITCODE) : banniere laissee intacte."
}

# La banniere et l'alt du README portent les memes mots : ils partent
# ensemble, sinon le texte qu'un lecteur d'ecran recoit prend du retard sur
# l'image, sans que personne le voie.
# Le splatting @derives, et non $derives : passe a une FONCTION, une variable
# tableau arrive comme un seul argument, alors qu'un binaire en recoit deux.
# Les tests remplacent git par une fonction ; sans splatting, ils mesureraient
# autre chose que ce que git recoit reellement.
$derives = @('assets/banner.svg', 'README.md')
$modifie = git status --porcelain -- @derives
if ([string]::IsNullOrWhiteSpace($modifie)) {
    Write-Host "Banniere inchangee, rien a pousser."
    exit 0
}

git --no-pager diff --stat -- @derives

if (-not $Push) {
    Write-Host ""
    Write-Host "La banniere a change. Relance avec -Push pour commiter et pousser."
    exit 0
}

# Scope aux seuls fichiers derives : `git commit` sans pathspec publierait tout
# ce qui traine dans l'index sous un message qui ne le mentionne pas.
git commit -m "chore(banner): regenerate the banner" -- @derives
if ($LASTEXITCODE -ne 0) { throw "git commit a echoue (code $LASTEXITCODE)." }
git push
if ($LASTEXITCODE -ne 0) { throw "git push a echoue (code $LASTEXITCODE)." }
Write-Host "Banniere poussee."
