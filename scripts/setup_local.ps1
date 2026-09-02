# ==============================================================================
# Local Pipeline Setup & Execution Script (PowerShell / Windows)
# ==============================================================================

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Automated Data Pipeline Infrastructure (Local)  " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Start LocalStack
Write-Host "`n[1/5] Starting LocalStack with Docker Compose..." -ForegroundColor Yellow
docker-compose up -d localstack

Write-Host "Waiting 5 seconds for LocalStack to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# 2. Provision Infrastructure with Terraform
Write-Host "`n[2/5] Provisioning S3 Bucket with Terraform..." -ForegroundColor Yellow
Set-Location -Path infrastructure
terraform init
terraform apply -auto-approve
Set-Location -Path ..

# 3. Seed Raw Data
Write-Host "`n[3/5] Seeding raw input data to LocalStack S3..." -ForegroundColor Yellow
$env:AWS_ACCESS_KEY_ID="test"
$env:AWS_SECRET_ACCESS_KEY="test"
$env:AWS_DEFAULT_REGION="us-east-1"
aws --endpoint-url=http://localhost:4566 s3 cp data/sample_raw.csv s3://my-pipeline-bucket/raw/input.csv

# 4. Build and Run ETL Container
Write-Host "`n[4/5] Building and running ETL application container..." -ForegroundColor Yellow
docker-compose build etl-app
docker-compose run --rm etl-app

# 5. Verify Output
Write-Host "`n[5/5] Verifying processed data in LocalStack S3..." -ForegroundColor Yellow
aws --endpoint-url=http://localhost:4566 s3 ls s3://my-pipeline-bucket/processed/
aws --endpoint-url=http://localhost:4566 s3 cp s3://my-pipeline-bucket/processed/output.csv -

Write-Host "`n==================================================" -ForegroundColor Green
Write-Host "  Pipeline execution & verification SUCCESSFUL!  " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
