# AWS Health Notifications

This solution deploys AWS Health Notifications to Teams and Slack. 

## Prerequisites

* Must be deployed in an account with at least AWS Business support. This is due to the fact that accessing the Health API programmatically (not through the Console) requires at least a Business Support plan: [external link](https://docs.aws.amazon.com/health/latest/ug/health-api.html)

## Deployment

### Cloudformation

1. Create a new stack in your desired account in region us-east-1 using the provided template aws-health.yml.

### Terraform

1. Make sure you have your AWS credentials and config setup correctly.
1. Modify the variable values in _terraform.tfvars_ as required:
    | Parameter | Description | Mandatory | Allowed values |
    | --- | --- | --- | --- |
    | aws_region | The AWS region for deployment. Should be left untouched. | yes | Any valid AWS region |
    | resource_prefix | The prefix for all resources. If empty, uniquenss of resource names is ensured. | no | Any valid alphanumeric string including dashes no longer than 7 characters. |
    | teams_hook_url | The Teams Hook URL. If omitted, no notifications to Teams. | no | Any valid url starting with https:// |
    | slack_hook_url | The Slack Hook URL. If omitted, no notifications to Slack. | no | Any valid url starting with https:// |
    | execution_rate | The execution rate in minutes. | yes | Any valid integer between 1 and 60 |
1. Run terraform init
1. Make sure to set your AWS profile to the desired profile before running the next step.
1. Run terraform apply
1. Specify a non-empty value for variable _profile_ referring to a valid AWS profile.
