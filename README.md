# aws-health

AWS Health Notifications with MS Teams

# Prerequisites

* Must be deployed in an account with at least AWS Business support. This is due to the fact that accessing the Health API programmatically (not through the Console) requires at least a Business Support plan: [external link](https://docs.aws.amazon.com/health/latest/ug/health-api.html)

# Deployment

## Cloudformation

1. Create a new stack in your desired account in region us-east-1 using the provided template aws-health.yml.

## Terraform

1. Adjust profile in the provider section of main.tf
1. Make sure you have your AWS credentials and config setup correctly.
1. Run terraform init
1. Run terraform apply
