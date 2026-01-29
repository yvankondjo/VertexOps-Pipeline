param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    [string]$Region = "europe-west1",
    [string]$ArtifactRepo = "ml-training",
    [string]$ServiceAccountName = "gh-actions-sa",
    [string]$WifPool = "gh-pool",
    [string]$WifProvider = "gh-provider",
    [string]$GithubRepo = "yvankondjo/VertexOps-Pipeline"
)

$ErrorActionPreference = "Stop"

Write-Host "Enabling required services..."
gcloud services enable artifactregistry.googleapis.com iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com

Write-Host "Creating Artifact Registry repo (if missing)..."
gcloud artifacts repositories describe $ArtifactRepo --location $Region --project $ProjectId 2>$null
if ($LASTEXITCODE -ne 0) {
    gcloud artifacts repositories create $ArtifactRepo --repository-format=docker --location=$Region --description="ML training images" --project $ProjectId
}

Write-Host "Creating Service Account (if missing)..."
$saEmail = "$ServiceAccountName@$ProjectId.iam.gserviceaccount.com"
gcloud iam service-accounts describe $saEmail --project $ProjectId 2>$null
if ($LASTEXITCODE -ne 0) {
    gcloud iam service-accounts create $ServiceAccountName --display-name "GitHub Actions CI/CD" --project $ProjectId
}

Write-Host "Granting IAM roles to Service Account..."
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$saEmail" --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$saEmail" --role="roles/storage.admin"

Write-Host "Creating Workload Identity Pool (if missing)..."
gcloud iam workload-identity-pools describe $WifPool --location=global --project $ProjectId 2>$null
if ($LASTEXITCODE -ne 0) {
    gcloud iam workload-identity-pools create $WifPool --location=global --display-name="GitHub Actions Pool" --project $ProjectId
}

Write-Host "Creating Workload Identity Provider (if missing)..."
gcloud iam workload-identity-pools providers describe $WifProvider --workload-identity-pool=$WifPool --location=global --project $ProjectId 2>$null
if ($LASTEXITCODE -ne 0) {
    gcloud iam workload-identity-pools providers create-oidc $WifProvider `
      --workload-identity-pool=$WifPool `
      --location=global `
      --display-name="GitHub Provider" `
      --issuer-uri="https://token.actions.githubusercontent.com" `
      --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" `
      --attribute-condition="assertion.repository=='$GithubRepo'" `
      --project $ProjectId
}

Write-Host "Binding GitHub repo to Service Account..."
$projectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
gcloud iam service-accounts add-iam-policy-binding $saEmail `
  --role="roles/iam.workloadIdentityUser" `
  --member="principalSet://iam.googleapis.com/projects/$projectNumber/locations/global/workloadIdentityPools/$WifPool/attribute.repository/$GithubRepo"

Write-Host "Done. Set these GitHub secrets:"
Write-Host "GCP_SERVICE_ACCOUNT=$saEmail"
Write-Host "GCP_WIF_PROVIDER=projects/$projectNumber/locations/global/workloadIdentityPools/$WifPool/providers/$WifProvider"