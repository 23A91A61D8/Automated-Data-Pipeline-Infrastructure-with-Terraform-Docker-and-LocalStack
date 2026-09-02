# ==============================================================================
# Terraform Variables Definition
# ==============================================================================

variable "aws_region" {
  description = "The AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for the ETL pipeline"
  type        = string
  default     = "my-pipeline-bucket"
}

variable "localstack_endpoint" {
  description = "The endpoint URL for LocalStack cloud emulation"
  type        = string
  default     = "http://localhost:4566"
}

variable "environment" {
  description = "The deployment environment (e.g. dev, test, ci, prod)"
  type        = string
  default     = "dev"
}
