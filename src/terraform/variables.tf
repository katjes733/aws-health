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

variable "aws_region" {
    description = "The AWS region for deployment."
    type        = string
    default     = "us-east-1"

    validation {
        condition     = can(regex("^[a-z]{2}-(gov-){0,1}(north|northeast|east|southeast|south|southwest|west|northwest|central)-[1-9]{1}$", var.aws_region))
        error_message = "Must be a valid AWS region."
    }
}

variable "tag_owner" {
    description = "value"
    type        = string

    validation {
        condition     = can(regex("^[\\w\\.]+\\@[\\w]+\\.[a-z]+$", var.tag_owner))
        error_message = "Must be a valid email address for the owner."
    }
}

variable "tag_type" {
    description = "value"
    type        = string
    default     = "Internal"

    validation {
        condition     = can(regex("^Internal|External$", var.tag_type))
        error_message = "Must be one of the following values only: Internal or External."
    }
}

variable "tag_usage" {
    description = "value"
    type        = string

    validation {
        condition     = can(regex("^Playground|Development|Qualification|Production|Control Tower$", var.tag_usage))
        error_message = "Must be one of the following values only: Playground, Development, Qualification, Production or Control Tower."
    }
}

variable "resource_prefix" {
    description = "The prefix for all resources. If empty, uniquenss of resource names is ensured."
    type        = string
    default     = "mac-"

    validation {
        condition     = can(regex("^$|^[a-z0-9-]{0,7}$", var.resource_prefix))
        error_message = "The resource_prefix must be empty or not be longer that 7 characters containing only the following characters: a-z0-9- ."
    }
}

variable "teams_hook_url" {
    description = "The Teams Hook URL."
    type        = string
    default     = ""

    validation {
        condition     = can(regex("^$|^https:\\/\\/[a-zA-Z0-9_\\-\\+]+(\\.[a-zA-Z0-9_\\-\\+]+)+\\/.+$", var.teams_hook_url))
        error_message = "The teams_hook_url must be empty or a valid URL beginning with https:// ."
    }
}

variable "slack_hook_url" {
    description = "The Slack Hook URL."
    type        = string
    default     = ""

    validation {
        condition     = can(regex("^$|^https:\\/\\/[a-zA-Z0-9_\\-\\+]+(\\.[a-zA-Z0-9_\\-\\+]+)+\\/.+$", var.slack_hook_url))
        error_message = "The slack_hook_url must be empty or a valid URL beginning with https:// ."
    }
}

variable "execution_rate" {
    description = "The execution rate in minutes."
    type        = number
    default     = 10

    validation {
        condition     = var.execution_rate >= 1 && var.execution_rate <= 60
        error_message = "The execution_rate must be between 1 and 60 minutes."
    }
}

variable "error_email" {
    description = "The email address to be notified in case of execution errors."
    type        = string
    default     = ""

    validation {
        condition     = can(regex("^$|^[\\w\\.]+\\@[\\w]+\\.[a-z]+$", var.error_email))
        error_message = "The error_email must empty or a valid email address."
    }
}