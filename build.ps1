$ErrorActionPreference = "Stop"
Push-Location -LiteralPath $PSScriptRoot

$distDir = Join-Path $PSScriptRoot "dist"
$buildDir = Join-Path $PSScriptRoot "build"

Remove-Item -LiteralPath $buildDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $distDir -Recurse -Force -ErrorAction SilentlyContinue

pyinstaller `
    --onefile `
    --console `
    --clean `
    --name jenv `
    --distpath $distDir `
    --workpath $buildDir `
    --icon assets\icon.ico `
    .\jenv.py

Write-Host "Build complete: $distDir\jenv.exe"
