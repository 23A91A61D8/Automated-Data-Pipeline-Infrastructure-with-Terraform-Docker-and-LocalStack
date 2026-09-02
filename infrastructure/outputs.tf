# ==============================================================================
# Terraform Outputs Definition
# ==============================================================================

output "bucket_name" {
  description = "The name of the created S3 bucket"
  value       = aws_s3_bucket.data_bucket.id
}

output "bucket_arn" {
  description = "The ARN of the created S3 bucket"
  value       = aws_s3_bucket.data_bucket.arn
}

output "aws_region" {
  description = "The AWS region configured for the pipeline"
  value       = var.aws_region
}

output "localstack_endpoint" {
  description = "The LocalStack endpoint URL used for S3 operations"
  value       = var.localstack_endpoint
}
