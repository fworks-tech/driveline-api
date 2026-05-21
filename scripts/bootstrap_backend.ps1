[CmdletBinding()]
param(
    [switch]$Detach
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repoRoot

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
    Write-Host 'Created .env from .env.example'
}

$composeArgs = @('compose', 'up', '--build')
if ($Detach) {
    $composeArgs += '-d'
}

Write-Host 'Starting the backend stack with Docker Compose...'
Write-Host 'This builds the image, runs migrations, and starts PostgreSQL, Redis, and Django.'

docker @composeArgs
