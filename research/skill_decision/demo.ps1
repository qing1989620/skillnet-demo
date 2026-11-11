param([string]$Python = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if ([string]::IsNullOrWhiteSpace($Python)) {
    $researchPython = Join-Path (Split-Path $projectRoot -Parent) '.venv-skill-quality/Scripts/python.exe'
    if (Test-Path -LiteralPath $researchPython) {
        $Python = $researchPython
    } else {
        $Python = (Get-Command python -ErrorAction Stop).Source
    }
}
Push-Location $projectRoot
try {
    & $Python -X utf8 -m research.skill_decision.demo
    if ($LASTEXITCODE -ne 0) { throw 'Offline method demonstration failed; use the existing research Python environment.' }
} finally { Pop-Location }
