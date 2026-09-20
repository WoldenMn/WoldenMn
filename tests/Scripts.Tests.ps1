#Requires -Modules @{ ModuleName = 'Pester'; ModuleVersion = '5.0' }
<#
    Garde les promesses des deux scripts PowerShell.

    Elles sont du meme ordre que celles de build_banner.py : ne rien publier
    qu'on n'ait verifie, et ne pas confondre « pas encore ecrit » avec « rate ».
    Chacune a deja ete enfreinte une fois.

    Lancer (Pester 5 sous Windows PowerShell 5.1, dont la strategie
    d'execution est souvent Restricted) :
        powershell -NoProfile -ExecutionPolicy Bypass -Command "Import-Module Pester -MinimumVersion 5.0.0; Invoke-Pester .\tests\Scripts.Tests.ps1"
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

Describe 'rafraichir.ps1, execute sous mocks' {
    # La premiere version de ces tests cherchait du texte dans le script. Une
    # contre-expertise du 2026-09-18 a retire le `exit 0` du bloc sans -Push :
    # le script enchainait alors commit et push, et les tests restaient verts.
    # Ils executent donc le script, avec git et python remplaces par des mocks
    # qui enregistrent chaque appel.

    BeforeAll { $script:Rafraichir = Join-Path $script:Racine 'rafraichir.ps1' }

    BeforeEach {
        Mock python { $global:LASTEXITCODE = 0 }
        Mock git {
            $global:LASTEXITCODE = 0
            if ($args[0] -eq 'status') { ' M assets/banner.svg' }
        }
        Mock Write-Host {}
    }

    It 'sans -Push, ne commite ni ne pousse rien' {
        Push-Location
        try { & $script:Rafraichir } finally { Pop-Location }
        Should -Invoke git -Exactly -Times 0 -ParameterFilter { $args -contains 'push' }
        Should -Invoke git -Exactly -Times 0 -ParameterFilter { $args -contains 'commit' }
    }

    It 'avec -Push, un seul commit, scope aux deux fichiers derives, puis un push' {
        # Un commit sans pathspec publie tout l'index sous un message qui ne le
        # mentionne pas : deux suppressions de workflow sont presque parties ainsi.
        # Les deux chemins vont ensemble : la banniere et l'alt du README portent
        # les memes chiffres, publier l'un sans l'autre les desaccorde.
        Push-Location
        try { & $script:Rafraichir -Push } finally { Pop-Location }
        Should -Invoke git -Exactly -Times 1 -ParameterFilter {
            $args[0] -eq 'commit' -and $args -contains 'assets/banner.svg' -and $args -contains 'README.md'
        }
        Should -Invoke git -Exactly -Times 0 -ParameterFilter {
            $args[0] -eq 'commit' -and -not ($args -contains 'assets/banner.svg' -and $args -contains 'README.md')
        }
        # Pas de verification du `--` : PowerShell le retire des arguments d'une
        # FONCTION, donc le mock ne le voit jamais, alors que le vrai binaire le
        # recoit. Le tester ici mesurerait le mock, pas git.
        Should -Invoke git -Exactly -Times 1 -ParameterFilter { $args[0] -eq 'push' -and $args.Count -eq 1 }
        Should -Invoke git -Exactly -Times 0 -ParameterFilter { $args[0] -eq 'push' -and $args.Count -gt 1 }
    }

    It 'leve et ne pousse rien quand git commit echoue' {
        Mock git {
            $global:LASTEXITCODE = if ($args[0] -eq 'commit') { 1 } else { 0 }
            if ($args[0] -eq 'status') { ' M assets/banner.svg' }
        }
        Push-Location
        try { { & $script:Rafraichir -Push } | Should -Throw -ExpectedMessage '*git commit a echoue*' } finally { Pop-Location }
        Should -Invoke git -Exactly -Times 0 -ParameterFilter { $args[0] -eq 'push' }
    }

    It 'leve quand git push echoue, au lieu d''annoncer la banniere publiee' {
        Mock git {
            $global:LASTEXITCODE = if ($args[0] -eq 'push') { 1 } else { 0 }
            if ($args[0] -eq 'status') { ' M assets/banner.svg' }
        }
        Push-Location
        try { { & $script:Rafraichir -Push } | Should -Throw -ExpectedMessage '*git push a echoue*' } finally { Pop-Location }
    }

    It 'ne publie rien quand les compteurs n''ont pas bouge' {
        Mock git { $global:LASTEXITCODE = 0 }
        Push-Location
        try { & $script:Rafraichir -Push } finally { Pop-Location }
        Should -Invoke git -Exactly -Times 0 -ParameterFilter { $args[0] -eq 'commit' }
        Should -Invoke git -Exactly -Times 0 -ParameterFilter { $args[0] -eq 'push' }
    }

    It 'ne publie rien quand build_banner.py echoue' {
        Mock python { $global:LASTEXITCODE = 1 }
        Push-Location
        try { { & $script:Rafraichir -Push } | Should -Throw -ExpectedMessage '*build_banner.py a echoue*' } finally { Pop-Location }
        Should -Invoke git -Exactly -Times 0 -ParameterFilter { $args[0] -in 'commit', 'push' }
    }

    It 'leve si python est introuvable, sans rien lancer' {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'python' }
        Push-Location
        try { { & $script:Rafraichir } | Should -Throw -ExpectedMessage '*python introuvable*' } finally { Pop-Location }
        Should -Invoke python -Exactly -Times 0
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

    Context 'Invoke-Externe' {
        # Le 2026-09-20, l'export a plante sous Windows PowerShell 5.1 : Edge
        # avait ecrit une ligne sur stderr faute de droits sur sa cle de mise a
        # jour, et $ErrorActionPreference = 'Stop' en a fait une erreur
        # terminante. Le meme script passait sous pwsh 7, d'ou un bug qui ne se
        # voyait pas la ou on le lancait.

        It 'ne leve pas quand le binaire ecrit sur stderr et sort a zero' {
            $ErrorActionPreference = 'Stop'
            { Invoke-Externe -Binaire $env:ComSpec `
                -Arguments @('/c', 'echo bruit 1>&2 & exit 0') } | Should -Not -Throw
        }

        It 'rend le code de sortie du binaire plutot que de l''ignorer' {
            $ErrorActionPreference = 'Stop'
            Invoke-Externe -Binaire $env:ComSpec -Arguments @('/c', 'exit 3') | Should -Be 3
        }

        # Pas de test sur la restauration de $ErrorActionPreference : la passe de
        # mutation a montre qu'il ne mordait pas. L'affectation dans la fonction
        # est locale a sa portee, donc l'appelant retrouve la sienne meme sans
        # rien restaurer. Le code qui allait avec a ete retire.
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
