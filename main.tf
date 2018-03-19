#
# ECS services service discovery using Route53 auto-naming
#

# lambda add/remove instances to service
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
