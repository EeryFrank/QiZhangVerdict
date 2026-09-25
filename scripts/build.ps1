param(
    [string]$GradleUserHome = 'E:\CodexTemp\QiZhangVerdict\gradle',
    [switch]$PluginOnly
)
$ErrorActionPreference = 'Stop'
$qvProject = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$env:GRADLE_USER_HOME = $GradleUserHome
New-Item -ItemType Directory -Force -Path $GradleUserHome | Out-Null
Push-Location $qvProject
try {
    & .\gradlew.bat --project-cache-dir (Join-Path $GradleUserHome 'project-root') build --console=plain
    if ($LASTEXITCODE -ne 0) { throw 'Core/plugin build failed.' }
    if (-not $PluginOnly) {
        foreach ($qvVersion in @('1.20.1','1.21.1')) {
            Push-Location (Join-Path $qvProject "platforms\$qvVersion")
            try {
                & .\gradlew.bat --project-cache-dir (Join-Path $GradleUserHome "project-$qvVersion") build --console=plain
                if ($LASTEXITCODE -ne 0) { throw "Mod build failed: $qvVersion" }
            } finally { Pop-Location }
        }
    }
    Write-Output 'Build finished. Run python scripts/package_release.py after reviewing validation evidence.'
} finally { Pop-Location }
