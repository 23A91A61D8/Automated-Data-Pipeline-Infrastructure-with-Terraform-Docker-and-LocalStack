# ==============================================================================
# Terraform Main Configuration
# Automated Data Pipeline Infrastructure - LocalStack AWS Emulation
# ==============================================================================

terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ------------------------------------------------------------------------------
# AWS Provider Configuration for LocalStack
# ------------------------------------------------------------------------------
# Points all AWS API calls to the local LocalStack emulator instead of real AWS.
# Dummy credentials and validation bypasses are required for offline emulation.
provider "aws" {
  region     = var.aws_region
  access_key = "test"
  secret_key = "test"

  # Prevent Terraform from attempting to contact real AWS authentication endpoints
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  # Force S3 path-style addressing (http://localhost:4566/bucket-name) for LocalStack stability
  s3_use_path_style = true

  # Override service endpoints to point to LocalStack
  endpoints {
    s3 = var.localstack_endpoint
  }
}

# ------------------------------------------------------------------------------
# S3 Bucket Resource
# ------------------------------------------------------------------------------
# Target S3 bucket used for raw data ingestion and processed ETL output storage.
resource "aws_s3_bucket" "data_bucket" {
  bucket = var.s3_bucket_name

  tags = {
    Name        = var.s3_bucket_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Project     = "Automated-Data-Pipeline"
  }
}
