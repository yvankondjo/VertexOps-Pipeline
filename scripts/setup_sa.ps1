param(
  [Parameter(Mandatory=$true)][string]$ProjectId,
  [string]$ServiceAccountName = "vertexops-airflow-sa",
  [string]$KeyOut = "secrets/gcp/sa.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$saEmail = "$ServiceAccountName@$ProjectId.iam.gserviceaccount.com"

function Assert-Ok($msg) {
  if ($LASTEXITCODE -ne 0) { throw "FAILED: $msg (exit=$LASTEXITCODE)" }
}

Write-Host "Using PROJECT_ID=$ProjectId"
gcloud config set project $ProjectId *> $null
Assert-Ok "gcloud config set project"

Write-Host "Enable IAM API..."
gcloud services enable iam.googleapis.com *> $null
Assert-Ok "enable iam.googleapis.com"

Write-Host "Check service account..."
gcloud iam service-accounts describe $saEmail *> $null
$exists = ($LASTEXITCODE -eq 0)

if (-not $exists) {
  Write-Host "SA not found. Creating..."
  gcloud iam service-accounts create $ServiceAccountName --display-name "VertexOps Airflow SA" *> $null
  Assert-Ok "create service account"

  # petite attente / retry (consistance éventuelle)
  $ok = $false
  for ($i=0; $i -lt 10; $i++) {
    gcloud iam service-accounts describe $saEmail *> $null
    if ($LASTEXITCODE -eq 0) { $ok = $true; break }
    Start-Sleep -Seconds 2
  }
  if (-not $ok) { throw "Service account still not visible after retries: $saEmail" }
} else {
  Write-Host "SA exists: $saEmail"
}

Write-Host "Grant roles (MVP)..."
gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$saEmail" --role "roles/storage.objectAdmin" *> $null
Assert-Ok "bind roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$saEmail" --role "roles/bigquery.jobUser" *> $null
Assert-Ok "bind roles/bigquery.jobUser"

gcloud projects add-iam-policy-binding $ProjectId --member "serviceAccount:$saEmail" --role "roles/bigquery.dataEditor" *> $null
Assert-Ok "bind roles/bigquery.dataEditor"

Write-Host "Create key file if missing..."
$dir = Split-Path $KeyOut -Parent
New-Item -ItemType Directory -Force $dir | Out-Null

$needKey = $true
if (Test-Path $KeyOut) {
  try {
    $json = Get-Content $KeyOut -Raw | ConvertFrom-Json
    if ($json.client_email -eq $saEmail) { $needKey = $false }
  } catch { $needKey = $true }
}

if ($needKey) {
  if (Test-Path $KeyOut) { Remove-Item $KeyOut -Force }
  gcloud iam service-accounts keys create $KeyOut --iam-account $saEmail *> $null
  Assert-Ok "create service account key"
  Write-Host "Created key: $KeyOut"
} else {
  Write-Host "Key already valid at $KeyOut (skipping)."
}

Write-Host "DONE ✅"
Write-Host " - SA: $saEmail"
Write-Host " - Key: $KeyOut"
