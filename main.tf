#
# ECS services service discovery using Route53 auto-naming
#

# tf setup namespace
# lambda add/remove instances to service

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

# TODO: option to use private to public namespace
resource "aws_service_discovery_private_dns_namespace" "this" {
  count       = "${module.enabled.value && ! module.enable_public_namespace.value ? 1 : 0}"
  name        = "${var.namespace}"
  description = "Service Discovery"
  vpc         = "${var.vpc_id}"
}

# id, arn, hosted_zone

