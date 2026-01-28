param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    [Parameter(Mandatory=$true)]
    [string]$Region,
    [Parameter(Mandatory=$true)]
    [string]$RepoName,
    [Parameter(Mandatory=$true)]
    [string]$ImageName,
    [Parameter(Mandatory=$true)]
    [string]$Tag
)

$ErrorActionPreference = "Stop"

$imageUri = "$Region-docker.pkg.dev/$ProjectId/$RepoName/$ImageName:$Tag"

Write-Host "Building $imageUri"
docker build -f ml/training/Dockerfile -t $imageUri .

Write-Host "Pushing $imageUri"
docker push $imageUri

Write-Host "Done: $imageUri"