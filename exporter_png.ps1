#Requires -Version 5.1
<#
.SYNOPSIS
    Rend les SVG du depot en PNG, aux dimensions exactes attendues par GitHub.
.DESCRIPTION
    L'avatar et l'apercu social sont dessines en SVG, mais GitHub n'accepte que
    du PNG, du JPG ou du GIF a l'upload. Ce script fait le pont, pour qu'aucun
    des deux fichiers a televerser ne soit un binaire orphelin qu'on ne sait
    plus regenerer.

    Le binaire Edge est CHERCHE, jamais suppose : son chemin porte un numero de
    version qui change a chaque mise a jour, et un chemin en dur casse en
    silence quelques semaines plus tard.

    Les PNG produits vont dans export/, hors du depot : ce sont des derives.
.EXAMPLE
    .\exporter_png.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Wait-Fichier {
    # Edge rend la main AVANT d'avoir vide son tampon sur le disque. Verifier
    # l'existence dans la foulee est une course, et elle repond 'absent' sur un
    # rendu parfaitement reussi. On attend que le fichier apparaisse, puis que sa
    # taille cesse de bouger.
    param([string]$Chemin, [int]$DelaiMax = 20)

    $fin = (Get-Date).AddSeconds($DelaiMax)
    $precedente = -1
    while ((Get-Date) -lt $fin) {
        if (Test-Path -LiteralPath $Chemin -PathType Leaf) {
            $taille = (Get-Item -LiteralPath $Chemin).Length
            if ($taille -gt 0 -and $taille -eq $precedente) { return $taille }
            $precedente = $taille
        }
        Start-Sleep -Milliseconds 250
    }
    return 0
}

function Get-CheminEdge {
    $racine = Join-Path ${env:ProgramFiles(x86)} 'Microsoft'
    $candidats = @()

    $core = Join-Path $racine 'EdgeCore'
    if (Test-Path -LiteralPath $core) {
        $candidats += Get-ChildItem -LiteralPath $core -Directory |
            Where-Object { $_.Name -as [version] } |
            Sort-Object { [version]$_.Name } -Descending |
            ForEach-Object { Join-Path $_.FullName 'msedge.exe' }
    }
    $candidats += Join-Path $racine 'Edge' | Join-Path -ChildPath 'Application' | Join-Path -ChildPath 'msedge.exe'

    foreach ($c in $candidats) { if (Test-Path -LiteralPath $c -PathType Leaf) { return $c } }
    throw "msedge.exe introuvable (cherche dans EdgeCore et Edge/Application) : impossible de rendre les PNG."
}

$edge = Get-CheminEdge
Write-Host "Edge : $edge"

$sorties = Join-Path $PSScriptRoot 'export'
if (-not (Test-Path -LiteralPath $sorties)) { New-Item -ItemType Directory -Path $sorties | Out-Null }

# Le facteur d'echelle double la definition : GitHub sert l'avatar sur des ecrans
# a forte densite, un 460 px nu y sort flou.
$cibles = @(
    @{ Svg = 'assets/avatar.svg';         Png = 'avatar.png';         L = 460;  H = 460;  Echelle = 2 }
    @{ Svg = 'assets/social-preview.svg'; Png = 'social-preview.png'; L = 1280; H = 640; Echelle = 1 }
)

$page = Join-Path $sorties '_rendu.html'
foreach ($c in $cibles) {
    $svg = Join-Path $PSScriptRoot $c.Svg
    if (-not (Test-Path -LiteralPath $svg -PathType Leaf)) { throw "source absente : $($c.Svg)" }

    $png = Join-Path $sorties $c.Png
    Remove-Item -LiteralPath $png -ErrorAction SilentlyContinue

    $uri = ([Uri]$svg).AbsoluteUri
    @"
<!doctype html><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:#12141a}
img{display:block;width:$($c.L)px;height:$($c.H)px}</style><img src="$uri">
"@ | Set-Content -LiteralPath $page -Encoding UTF8

    & $edge --headless --disable-gpu --hide-scrollbars `
            "--force-device-scale-factor=$($c.Echelle)" `
            "--screenshot=$png" "--window-size=$($c.L),$($c.H)" `
            ([Uri]$page).AbsoluteUri 2>$null | Out-Null

    $octets = Wait-Fichier -Chemin $png
    if ($octets -eq 0) { throw "Edge n'a rien ecrit pour $($c.Png) apres 20 s d'attente." }
    $ko = [math]::Round($octets / 1KB, 1)
    if ($ko -le 1) { throw "$($c.Png) fait $ko Ko : rendu vide, refus de le garder." }
    Write-Host ("  {0,-22} {1,6} Ko  ({2}x{3})" -f $c.Png, $ko, ($c.L * $c.Echelle), ($c.H * $c.Echelle))
}
Remove-Item -LiteralPath $page -ErrorAction SilentlyContinue
Write-Host "PNG a jour dans export/."
