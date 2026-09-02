#!/usr/bin/env bash
# ==============================================================================
# Local Pipeline Setup & Execution Script (Bash / Linux / macOS)
# ==============================================================================

set -e

echo "=================================================="
echo "  Automated Data Pipeline Infrastructure (Local)  "
echo "=================================================="

# 1. Start LocalStack
echo -e "\n[1/5] Starting LocalStack with Docker Compose..."
docker-compose up -d localstack

echo "Waiting for LocalStack S3 edge service..."
until curl -s http://localhost:4566/_localstack/health | grep -q 's3'; do
  echo "Waiting for LocalStack..."
  sleep 2
done

# 2. Provision Infrastructure with Terraform
echo -e "\n[2/5] Provisioning S3 Bucket with Terraform..."
cd infrastructure
terraform init
terraform apply -auto-approve
cd ..

# 3. Seed Raw Data
echo -e "\n[3/5] Seeding raw input data to LocalStack S3..."
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

aws --endpoint-url=http://localhost:4566 s3 cp data/sample_raw.csv s3://my-pipeline-bucket/raw/input.csv

# 4. Build and Run ETL Container
echo -e "\n[4/5] Building and running ETL application container..."
docker-compose build etl-app
docker-compose run --rm etl-app

# 5. Verify Output
echo -e "\n[5/5] Verifying processed data in LocalStack S3..."
aws --endpoint-url=http://localhost:4566 s3 ls s3://my-pipeline-bucket/processed/
aws --endpoint-url=http://localhost:4566 s3 cp s3://my-pipeline-bucket/processed/output.csv -

echo -e "\n=================================================="
echo "  Pipeline execution & verification SUCCESSFUL!  "
echo "=================================================="
