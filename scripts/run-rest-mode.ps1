param(
    [string]$Transport = "rest"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path "source/ebi.py")) {
    throw "Run this script from the repository root."
}

$env:EBI_API_TRANSPORT = $Transport
Write-Host "EBI_API_TRANSPORT=$($env:EBI_API_TRANSPORT)"

if ($env:EBI_REST_ACCESS_TOKEN) {
    Write-Host "Using EBI_REST_ACCESS_TOKEN from environment."
} elseif ($env:EBI_REST_ADMIN_TOKEN) {
    Write-Host "Using EBI_REST_ADMIN_TOKEN from environment."
} else {
    Write-Host "No REST token set; client will use cookie session login."
}

python source/ebi.py
