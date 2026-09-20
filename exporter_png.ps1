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

function Test-PngComplet {
    <#
        Un PNG commence par une signature de 8 octets et se termine par le chunk
        IEND. Tant que ces 16 octets ne sont pas tous la, le fichier est encore
        en cours d'ecriture, quoi qu'en dise sa taille.

        Ouverture en partage lecture ET ecriture : Edge tient encore le fichier.
    #>
    param([string]$Chemin)

    $SIGNATURE = [byte[]](137, 80, 78, 71, 13, 10, 26, 10)
    $FIN_IEND  = [byte[]](73, 69, 78, 68, 174, 66, 96, 130)

    $flux = $null
    try {
        $flux = [System.IO.File]::Open($Chemin, [System.IO.FileMode]::Open,
                                       [System.IO.FileAccess]::Read,
                                       [System.IO.FileShare]::ReadWrite)
        if ($flux.Length -lt ($SIGNATURE.Length + $FIN_IEND.Length)) { return $false }

        $tampon = New-Object byte[] 8
        if ($flux.Read($tampon, 0, 8) -ne 8) { return $false }
        if (@(Compare-Object $tampon $SIGNATURE -SyncWindow 0).Count) { return $false }

        [void]$flux.Seek(-8, [System.IO.SeekOrigin]::End)
        if ($flux.Read($tampon, 0, 8) -ne 8) { return $false }
        return -not @(Compare-Object $tampon $FIN_IEND -SyncWindow 0).Count
    } catch {
        return $false        # verrou, troncature, disparition : pas pret, on repasse
    } finally {
        if ($flux) { $flux.Dispose() }
    }
}

function Wait-Fichier {
    <#
        Edge rend la main AVANT d'avoir vide son tampon sur le disque. Verifier
        l'existence dans la foulee est une course, et elle repond 'absent' sur un
        rendu parfaitement reussi.

        On a d'abord attendu que la TAILLE cesse de bouger. Un test l'a refute le
        2026-09-06 : deux lectures identiques ne prouvent pas la fin de l'ecriture,
        seulement que rien n'a bouge pendant l'intervalle de scrutation. Sur un
        fichier ecrit par morceaux, la fonction rendait 1 Ko sur 10. Un PNG
        tronque, et personne pour le voir.

        On lit donc la complétude DANS le fichier, ce qui ne depend d'aucun
        chronometre. Rend la taille du PNG complet, ou 0 si le delai expire.
    #>
    param([string]$Chemin, [int]$DelaiMax = 20)

    $fin = (Get-Date).AddSeconds($DelaiMax)
    while ((Get-Date) -lt $fin) {
        if ((Test-Path -LiteralPath $Chemin -PathType Leaf) -and (Test-PngComplet $Chemin)) {
            return (Get-Item -LiteralPath $Chemin).Length
        }
        Start-Sleep -Milliseconds 150
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

function Invoke-Externe {
    <#
        Windows PowerShell 5.1 transforme la moindre ligne de stderr d'un binaire
        en erreur terminante quand $ErrorActionPreference vaut 'Stop', meme
        redirigee vers $null et meme quand le binaire sort a 0. Edge ecrit ce
        bruit des qu'il n'a pas les droits sur sa cle de mise a jour, ce qui
        depend du poste et de la session. Le seul verdict qui vaille est le code
        de sortie.

        Rien a restaurer en sortie : l'affectation ci-dessous cree une variable
        locale a la fonction, l'appelant garde la sienne. Verifie plutot que
        suppose, et un try/finally ici ne serait qu'un ornement.
    #>
    param([string]$Binaire, [string[]]$Arguments)

    $ErrorActionPreference = 'Continue'
    & $Binaire @Arguments 2>$null | Out-Null
    return $LASTEXITCODE
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

    # Le rendu va dans un fichier a cote : un echec ne doit pas laisser
    # l'utilisateur sans PNG du tout. L'ancien n'est remplace qu'une fois le
    # nouveau juge complet.
    $png = Join-Path $sorties $c.Png
    $provisoire = Join-Path $sorties ($c.Png -replace '\.png$', '.nouveau.png')
    Remove-Item -LiteralPath $provisoire -ErrorAction SilentlyContinue

    $uri = ([Uri]$svg).AbsoluteUri
    @"
<!doctype html><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:#12141a}
img{display:block;width:$($c.L)px;height:$($c.H)px}</style><img src="$uri">
"@ | Set-Content -LiteralPath $page -Encoding UTF8

    $code = Invoke-Externe -Binaire $edge -Arguments @(
        '--headless', '--disable-gpu', '--hide-scrollbars',
        "--force-device-scale-factor=$($c.Echelle)",
        "--screenshot=$provisoire", "--window-size=$($c.L),$($c.H)",
        ([Uri]$page).AbsoluteUri)

    $octets = Wait-Fichier -Chemin $provisoire
    if ($octets -eq 0) {
        throw "Edge n'a rien ecrit pour $($c.Png) apres 20 s d'attente (code de sortie $code). L'ancien PNG est intact."
    }
    $ko = [math]::Round($octets / 1KB, 1)
    if ($ko -le 1) {
        Remove-Item -LiteralPath $provisoire -ErrorAction SilentlyContinue
        throw "$($c.Png) fait $ko Ko : rendu vide, refus de le garder. L'ancien PNG est intact."
    }
    Move-Item -LiteralPath $provisoire -Destination $png -Force
    Write-Host ("  {0,-22} {1,6} Ko  ({2}x{3})" -f $c.Png, $ko, ($c.L * $c.Echelle), ($c.H * $c.Echelle))
}
Remove-Item -LiteralPath $page -ErrorAction SilentlyContinue
Write-Host "PNG a jour dans export/."
