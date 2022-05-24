# MIT License
#
# Copyright (c) 2022 Martin Macecek
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

terraform {
    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "~> 4.13.0"
        }
    }

    required_version = ">= 0.14.9"

    backend "s3" {
        bucket         = "rearc-terraform-state-bucket-275279264324-us-east-1"
        key            = "state/terraform.tfstate"
        region         = "us-east-1"
        encrypt        = true
        kms_key_id     = "alias/rearc-terraform-state-bucket-key"
        dynamodb_table = "rearc-terraform-state"
    }
}

provider "aws" {
  region  = var.aws_region
}

data "aws_partition" "current" {}

data "aws_region" "current" {}

locals {
    is_arm_supported_region = contains(["us-east-1", "us-west-2", "eu-central-1", "eu-west-1", "ap-south-1", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1"], data.aws_region.current.name)
    aws_health_notification_lambda_function_name = "%{ if var.resource_prefix != "" }${var.resource_prefix}%{ else }${random_string.unique_id}-%{ endif }AwsHealthNotification"
}

resource "random_string" "unique_id" {
    count   = var.resource_prefix == "" ? 1 : 0
    length  = 8
    special = false  
}

resource "aws_iam_role" "aws_health_notification_lambda_role" {
    name = var.resource_prefix != "" ? "${var.resource_prefix}AwsHealthNotificationLambdaRole" : null
    managed_policy_arns = [
        "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        aws_iam_policy.aws_health_notification_lambda_role_policy.arn
    ]
    assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Action = "sts:AssumeRole"
                Effect = "Allow"
                Principal = {
                    Service = "lambda.amazonaws.com"
                }
            },
        ]
    })
}

resource "aws_iam_policy" "aws_health_notification_lambda_role_policy" {
    name = "%{ if var.resource_prefix != "" }${var.resource_prefix}%{ else }${random_string.unique_id}-%{ endif }AwsHealthNotificationLambdaRolePolicy"
    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Action   = ["health:DescribeEvents"]
                Effect   = "Allow"
                Resource = "*"
            },
            {
                Action   = ["health:DescribeEventDetails"]
                Effect   = "Allow"
                Resource = "arn:aws:health:*::event/*/*/*"
            },
        ]
    })
}

resource "aws_cloudwatch_log_group" "aws_health_notification_lambda_log_group" {
    name = "/aws/lambda/${local.aws_health_notification_lambda_function_name}"
    retention_in_days = 7
}

data "archive_file" "aws_health_package" {
    type = "zip"
    source_file = "${path.module}/python/aws_health.py"
    output_path = "${path.module}/.package/aws_health.zip"
}

resource "aws_lambda_function" "aws_health_notification_lambda" {
    depends_on = [
        aws_cloudwatch_log_group.aws_health_notification_lambda_log_group
    ]
    function_name = "${local.aws_health_notification_lambda_function_name}"
    architectures = local.is_arm_supported_region ? ["arm64"] : ["x86_64"]
    filename = "${path.module}/.package/aws_health.zip"
    source_code_hash = data.archive_file.aws_health_package.output_base64sha256
    handler = "aws_health.lambda_handler"
    runtime = "python3.9"
    memory_size = 128
    timeout = 60
    role = aws_iam_role.aws_health_notification_lambda_role.arn
    environment {
      variables = {
        "TeamsHookUrl" = "${var.teams_hook_url}",
        "SlackHookUrl" = "${var.slack_hook_url}",
        "CheckTime" = "${var.execution_rate}"
      }
    }
}

resource "aws_cloudwatch_event_rule" "aws_health_notification_event_rule_on_schedule" {
    name = "%{ if var.resource_prefix != "" }${var.resource_prefix}%{ else }${random_string.unique_id}-%{ endif }AwsHealthNotificationEventRuleOnSchedule"
    description = "Scheduled rule to trigger check for AWS Health"
    schedule_expression = "rate(${var.execution_rate} %{ if var.execution_rate == 1 }minute%{ else }minutes%{ endif })"    
}

resource "aws_cloudwatch_event_target" "aws_health_notification_event_rule_on_schedule_target" {
    rule      = "${aws_cloudwatch_event_rule.aws_health_notification_event_rule_on_schedule.name}"
    target_id = "%{ if var.resource_prefix != "" }${var.resource_prefix}%{ else }${random_string.unique_id}-%{ endif }AwsHealthNotificationEventRuleOnScheduleTarget"
    arn       = "${aws_lambda_function.aws_health_notification_lambda.arn}"
}

resource "aws_lambda_permission" "aws_health_notification_lambda_permission" {
    statement_id  = "%{ if var.resource_prefix != "" }${var.resource_prefix}%{ else }${random_string.unique_id}-%{ endif }AwsHealthNotificationLambdaPermission"
    action        = "lambda:InvokeFunction"
    function_name = "${aws_lambda_function.aws_health_notification_lambda.function_name}"
    principal     = "events.amazonaws.com"
    source_arn    = "${aws_cloudwatch_event_rule.aws_health_notification_event_rule_on_schedule.arn}"
}
