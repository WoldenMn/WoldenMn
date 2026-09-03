#Requires -Version 5.1
<#
.SYNOPSIS
    Regenere assets/banner.svg depuis l'API GitHub, puis publie si les compteurs ont bouge.
.DESCRIPTION
    Les trois compteurs de la banniere sont des faits derives : ils ont un gardien
    plutot qu'une valeur ecrite a la main qui derive en silence. Ce script est ce
    gardien, joue a la demande. Sans donnees fraiches, build_banner.py echoue au
    lieu d'ecrire un chiffre perime, et ce script s'arrete avec lui.
.PARAMETER Push
    Commite et pousse le SVG regenere. Sans ce commutateur, le script se contente
    de regenerer et d'afficher ce qui a change.
.EXAMPLE
    .\rafraichir.ps1
    .\rafraichir.ps1 -Push
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

$modifie = git status --porcelain -- assets/banner.svg
if ([string]::IsNullOrWhiteSpace($modifie)) {
    Write-Host "Compteurs inchanges, rien a publier."
    exit 0
}

git --no-pager diff --stat -- assets/banner.svg

if (-not $Push) {
    Write-Host ""
    Write-Host "Les compteurs ont bouge. Relance avec -Push pour commiter et publier."
    exit 0
}

# Scope au seul banner.svg : `git commit` sans pathspec publierait tout ce qui
# traine dans l'index sous un message qui ne le mentionne pas.
git commit -m "chore(banner): refresh derived counters" -- assets/banner.svg
if ($LASTEXITCODE -ne 0) { throw "git commit a echoue (code $LASTEXITCODE)." }
git push
if ($LASTEXITCODE -ne 0) { throw "git push a echoue (code $LASTEXITCODE)." }
Write-Host "Banniere publiee."
