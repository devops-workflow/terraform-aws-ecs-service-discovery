#
# ECS services service discovery using Route53 auto-naming
#

# lambda add/remove instances to service
# CloudWatch event rule for triggering lambda

# Put create service in ecs-service module as an option

# https://www.terraform.io/docs/providers/aws/r/service_discovery_private_dns_namespace.html

module "enabled" {
  source  = "devops-workflow/boolean/local"
  version = "0.1.1"
  value   = "${var.enabled}"
}

module "enable_public_namespace" {
  source  = "devops-workflow/boolean/local"
  version = "0.1.1"
  value   = "${var.enable_public_namespace}"
}

//
// Route53 Service Discovery
//
resource "aws_service_discovery_private_dns_namespace" "this" {
  count       = "${module.enabled.value && ! module.enable_public_namespace.value ? 1 : 0}"
  name        = "${var.namespace}"
  description = "Service Discovery"
  vpc         = "${var.vpc_id}"
}

#Attributes: id, arn, hosted_zone
resource "aws_service_discovery_public_dns_namespace" "this" {
  count       = "${module.enabled.value && module.enable_public_namespace.value ? 1 : 0}"
  name        = "${var.namespace}"
  description = "Service Discovery"
}

#Attributes: id, arn, hosted_zone

//
// Lambda for adding/removing instances in service discovery
//
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.lambda_name}"
  retention_in_days = 14

  tags {
    "Description" = "Service Discovery lambda logs"
    "Environment" = "${var.environment}"
    "terraform"   = "true"
  }
}

# IAM give lambda access to read ec2, r
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = [
      "sts:AssumeRole",
    ]

    principals {
      type = "Service"

      identifiers = [
        "lambda.amazonaws.com",
      ]
    }

    effect = "Allow"
  }
}

data "aws_iam_policy_document" "lambda_perms" {
  statement {
    actions = [
      "ec2:CreateNetworkInterface",
      "ec2:DeleteNetworkInterface",
      "ec2:DescribeInstances",
      "ec2:DescribeNetworkInterfaces",
      "ecs:DescribeContainerInstances",
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "route53:ChangeResourceRecordSets",
      "route53:CreateHealthCheck",
      "route53:DeleteHealthCheck",
      "route53:GetHealthCheck",
      "route53:GetHostedZone",
      "route53:ListHostedZonesByName",
      "route53:UpdateHealthCheck",
      "servicediscovery:DeregisterInstance",
      "servicediscovery:Get*",
      "servicediscovery:List*",
      "servicediscovery:RegisterInstance",
    ]

    effect    = "Allow"
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "LambdaPerms" {
  name   = "LambdaSeviceDiscoveryPermissions"
  role   = "${aws_iam_role.iam_for_lambda.id}"
  policy = "${data.aws_iam_policy_document.lambda_perms.json}"
}

resource "aws_iam_role" "iam_for_lambda" {
  name               = "service-discovery"
  path               = "/lambda/"
  assume_role_policy = "${data.aws_iam_policy_document.lambda_assume_role.json}"
}

data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/src/"
  output_path = "lambda.zip"
}

resource "aws_lambda_function" "this" {
  depends_on = [
    "aws_cloudwatch_log_group.lambda",
  ]

  description      = "Service Discovery"
  filename         = "${data.archive_file.lambda.output_path}"
  function_name    = "${var.lambda_name}"
  role             = "${aws_iam_role.iam_for_lambda.arn}"
  handler          = "lambda_handler.lambda_handler"
  source_code_hash = "${base64sha256(file("${data.archive_file.lambda.output_path}"))}"
  runtime          = "python2.7"
  publish          = true
  timeout          = 20

  tags {
    "Description" = "Service Discovery"
    "terraform"   = "true"
  }
}

resource "aws_lambda_alias" "this" {
  name             = "servicediscovery"
  description      = "Latest Service Discovery lambda"
  function_name    = "${aws_lambda_function.this.function_name}"
  function_version = "${aws_lambda_function.this.version}"
}

resource "aws_lambda_permission" "this" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.this.function_name}"
  principal     = "events.amazonaws.com"
  source_arn    = "${aws_cloudwatch_event_rule.this.arn}"
  qualifier     = "${aws_lambda_alias.this.name}"
}

//
// Event rule and trigger for lambda
//
resource "aws_cloudwatch_event_rule" "this" {
  name        = "ecs-task-state-change"
  description = "Capture ECS task state changes"

  #role_arn to run target (lambda)
  #is_enabled

  event_pattern = <<PATTERN
{
  "source": [
    "aws.ecs"
  ],
  "detail-type": [
    "ECS Task State Change"
  ]
}
PATTERN
}

resource "aws_cloudwatch_event_target" "this" {
  rule      = "${aws_cloudwatch_event_rule.this.name}"
  target_id = "EcsTaskStateChangeSendToLambda"
  arn       = "${aws_lambda_alias.this.arn}"

  #role_arn
}

# Missing something for trigger to show up in lambda

