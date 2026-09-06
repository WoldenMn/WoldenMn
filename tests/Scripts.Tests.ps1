#Requires -Modules @{ ModuleName = 'Pester'; ModuleVersion = '5.0' }
<#
    Garde les promesses des deux scripts PowerShell.

    Elles sont du meme ordre que celles de build_banner.py : ne rien publier
    qu'on n'ait verifie, et ne pas confondre « pas encore ecrit » avec « rate ».
    Chacune a deja ete enfreinte une fois.

    Lancer (Pester 5 vit sous Windows PowerShell 5.1 sur ce poste) :
        powershell -NoProfile -Command "Invoke-Pester .\tests\Scripts.Tests.ps1"
#>

BeforeAll {
    $script:Racine = Split-Path -Parent $PSScriptRoot

    # exporter_png.ps1 s'execute des qu'on le dot-source : il rendrait les PNG a
    # chaque passage de la suite. On extrait donc ses fonctions par leur texte.
    #
    # Elles sont chargees comme un module en memoire plutot que par
    # Invoke-Expression : Pester 5 isole les portees, et une fonction definie
    # dans BeforeAll n'atteint pas les blocs It. Import-Module -Global, si.
    $src = Get-Content (Join-Path $script:Racine 'exporter_png.ps1') -Raw
    $debut = $src.IndexOf('function Test-PngComplet')
    $fin = $src.IndexOf('$edge = Get-CheminEdge')
    if ($debut -lt 0 -or $fin -lt 0) { throw 'fonctions introuvables dans exporter_png.ps1' }

    New-Module -Name FonctionsExport -ScriptBlock ([scriptblock]::Create($src.Substring($debut, $fin - $debut))) |
        Import-Module -Force -Global

    # Un PNG minimal mais valide au regard de ce que la fonction verifie :
    # signature de 8 octets, du remplissage, puis le chunk IEND.
    function script:New-OctetsPng {
        param([int]$Remplissage = 512)
        $signature = [byte[]](137, 80, 78, 71, 13, 10, 26, 10)
        $corps = [byte[]]::new($Remplissage)
        $iend = [byte[]](0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130)
        $signature + $corps + $iend
    }

    function script:New-CheminTemporaire {
        param([string]$Suffixe)
        Join-Path $env:TEMP "pester-$Suffixe-$PID-$(Get-Random).bin"
    }
}

Describe 'rafraichir.ps1' {

    BeforeAll { $script:Source = Get-Content (Join-Path $script:Racine 'rafraichir.ps1') -Raw }

    It 'scope son commit au seul banner.svg' {
        # Regression : un `git commit` sans pathspec publie tout l'index sous un
        # message qui ne le mentionne pas. C'etait le cas, et deux suppressions de
        # workflow seraient parties en douce sous un « refresh counters ».
        $commit = $script:Source -split "`n" | Where-Object { $_ -match '^\s*git commit' }

        $commit | Should -Not -BeNullOrEmpty
        foreach ($ligne in $commit) {
            $ligne | Should -Match '--\s+assets/banner\.svg' -Because 'un commit nu emporterait tout l''index'
        }
    }

    It 'refuse de partir si python est absent' {
        $script:Source | Should -Match 'Get-Command python'
        $script:Source | Should -Match 'throw'
    }

    It 'ne publie jamais sans le commutateur -Push' {
        $script:Source | Should -Match '\$Push'
        $script:Source | Should -Match 'if \(-not \$Push\)'
    }
}

Describe 'exporter_png.ps1' {

    Context 'Get-CheminEdge' {

        It 'trouve un binaire reel sur ce poste' {
            Get-CheminEdge | Should -Exist
        }

        It 'leve plutot que de rendre un chemin qui n''existe pas' {
            $sauve = ${env:ProgramFiles(x86)}
            try {
                ${env:ProgramFiles(x86)} = Join-Path $env:TEMP 'aucun-programfiles-ici'
                { Get-CheminEdge } | Should -Throw -ExpectedMessage '*introuvable*'
            } finally {
                ${env:ProgramFiles(x86)} = $sauve
            }
        }
    }

    Context 'Wait-Fichier' {
        # Edge rend la main avant d'avoir fini d'ecrire. La premiere version de
        # cette fonction attendait que la TAILLE cesse de bouger ; un test l'a
        # refutee le 2026-09-06 en rendant 1 Ko sur 10. Deux lectures identiques
        # ne prouvent rien d'autre que l'immobilite pendant l'intervalle. La
        # complétude se lit maintenant DANS le fichier, signature et chunk IEND.

        It 'rend 0 sur un fichier qui n''arrive jamais' {
            Wait-Fichier -Chemin (New-CheminTemporaire 'absent') -DelaiMax 2 | Should -Be 0
        }

        It 'refuse un fichier vide, et attend vraiment au lieu de rendre 0 tout de suite' {
            # Le retour seul ne prouve rien : une version cassee qui accepte
            # n'importe quelle taille rend 0 elle aussi sur un fichier vide, juste
            # sans attendre. C'est la DUREE qui discrimine.
            $vide = New-CheminTemporaire 'vide'
            New-Item -ItemType File -Path $vide -Force | Out-Null
            try {
                $chrono = [System.Diagnostics.Stopwatch]::StartNew()
                $taille = Wait-Fichier -Chemin $vide -DelaiMax 2
                $chrono.Stop()

                $taille | Should -Be 0
                $chrono.Elapsed.TotalSeconds | Should -BeGreaterThan 1 -Because 'un fichier vide doit epuiser le delai au lieu d''etre declare pret'
            } finally { Remove-Item $vide -ErrorAction SilentlyContinue }
        }

        It 'refuse un fichier bien dodu qui n''est pas un PNG' {
            # Le piege que la version « taille stable » n'attrapait pas : un
            # fichier parfaitement immobile, mais qui n'est pas une image.
            $leurre = New-CheminTemporaire 'leurre'
            [System.IO.File]::WriteAllBytes($leurre, [byte[]]::new(50000))
            try { Wait-Fichier -Chemin $leurre -DelaiMax 2 | Should -Be 0 }
            finally { Remove-Item $leurre -ErrorAction SilentlyContinue }
        }

        It 'refuse un fichier qui finit par IEND sans commencer par la signature' {
            # Sans ce test, retirer la verification de signature ne casse rien :
            # la mutation survivait. Un fichier peut tres bien porter le chunk
            # final d'un PNG sans en etre un.
            $faux = New-CheminTemporaire 'sans-signature'
            $iend = [byte[]](0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130)
            [System.IO.File]::WriteAllBytes($faux, [byte[]]::new(2048) + $iend)
            try { Wait-Fichier -Chemin $faux -DelaiMax 2 | Should -Be 0 }
            finally { Remove-Item $faux -ErrorAction SilentlyContinue }
        }

        It 'rend la taille d''un PNG complet' {
            $png = New-CheminTemporaire 'complet'
            $octets = New-OctetsPng -Remplissage 4096
            [System.IO.File]::WriteAllBytes($png, $octets)
            try { Wait-Fichier -Chemin $png -DelaiMax 5 | Should -Be $octets.Length }
            finally { Remove-Item $png -ErrorAction SilentlyContinue }
        }

        It 'attend le chunk final, pas la premiere taille venue' {
            # LE test de la fonction. Le corps arrive d'abord, IEND ensuite : tant
            # qu'il manque, rendre une taille reviendrait a livrer un PNG tronque.
            $partiel = New-CheminTemporaire 'partiel'
            $complet = New-OctetsPng -Remplissage 8192
            $sansFin = $complet[0..($complet.Length - 13)]
            [System.IO.File]::WriteAllBytes($partiel, $sansFin)

            $job = Start-Job -ScriptBlock {
                Start-Sleep -Milliseconds 800
                $flux = [System.IO.File]::Open($using:partiel, 'Append', 'Write', 'ReadWrite')
                $iend = [byte[]](0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130)
                $flux.Write($iend, 0, $iend.Length)
                $flux.Dispose()
            }
            try {
                $taille = Wait-Fichier -Chemin $partiel -DelaiMax 15
                $taille | Should -Be $complet.Length -Because 'rendre avant IEND, c''est livrer un PNG tronque'
            } finally {
                Remove-Job $job -Force -ErrorAction SilentlyContinue
                Remove-Item $partiel -ErrorAction SilentlyContinue
            }
        }

        It 'attend un PNG qui arrive en retard, au lieu de le rater' {
            $tardif = New-CheminTemporaire 'tardif'
            $job = Start-Job -ScriptBlock {
                Start-Sleep -Milliseconds 900
                $signature = [byte[]](137, 80, 78, 71, 13, 10, 26, 10)
                $iend = [byte[]](0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130)
                [System.IO.File]::WriteAllBytes($using:tardif, $signature + [byte[]]::new(1024) + $iend)
            }
            try {
                Wait-Fichier -Chemin $tardif -DelaiMax 15 | Should -BeGreaterThan 0
            } finally {
                Remove-Job $job -Force -ErrorAction SilentlyContinue
                Remove-Item $tardif -ErrorAction SilentlyContinue
            }
        }
    }
}
