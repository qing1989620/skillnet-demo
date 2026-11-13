param([string]$TexBin = 'D:/zhuomian_app/latex/texlive/2026/bin/windows')
$ErrorActionPreference = 'Stop'
$paperRoot = $PSScriptRoot
$env:PATH = $TexBin + ';' + $env:PATH
$engine = Join-Path $TexBin 'xelatex.exe'
$bibtex = Join-Path $TexBin 'bibtex.exe'
if (-not (Test-Path -LiteralPath $engine)) { throw 'XeLaTeX not found; pass -TexBin to your TeX Live binary directory.' }
Push-Location $paperRoot
try {
    New-Item -ItemType Directory -Force -Path build | Out-Null
    & $engine -interaction=nonstopmode -halt-on-error -file-line-error -no-shell-escape -output-directory=build main.tex
    if ($LASTEXITCODE -ne 0) { throw 'First XeLaTeX pass failed.' }
    & $bibtex build/main
    if ($LASTEXITCODE -ne 0) { throw 'BibTeX failed.' }
    1..2 | ForEach-Object {
        & $engine -interaction=nonstopmode -halt-on-error -file-line-error -no-shell-escape -output-directory=build main.tex
        if ($LASTEXITCODE -ne 0) { throw 'XeLaTeX reference pass failed.' }
    }
    Copy-Item -LiteralPath build/main.pdf -Destination SkillNet_中文研究论文.pdf -Force
    Write-Output 'Compiled SkillNet_中文研究论文.pdf'
} finally { Pop-Location }
